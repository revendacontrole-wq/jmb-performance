import os
import io
import uuid
import json
import pandas as pd
import openpyxl
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from app.models import User, PerformanceRecord, DailyPerformanceRecord, ImportHistory
from app.auth import clean_cpf, mask_cpf, hash_password

PREVIEW_CACHE: Dict[str, Dict[str, Any]] = {}

def parse_excel_file(contents: bytes, filename: str, competencia_input: str) -> Dict[str, Any]:
    """
    Parses uploaded Excel workbook bytes in memory and builds a Preview payload.
    Extracts monthly summary AND exact daily indicator breakdown (31 days) for all active employees.
    Guarantees 31-day daily calendar breakdown for 100% of active employees.
    """
    errors: List[Dict[str, str]] = []

    file_stream = io.BytesIO(contents)
    xl = pd.ExcelFile(file_stream, engine="openpyxl")
    sheet_names = xl.sheet_names

    # 1. Base Mot Master Authority
    mot_base_map = {}
    if "Base Mot" in sheet_names:
        try:
            df_bm = pd.read_excel(xl, sheet_name="Base Mot")
            for _, row in df_bm.iterrows():
                cod_val = row.get("Cód.Motorista") or row.get("Codigo") or row.get("Cód")
                cpf_val = row.get("CPF")
                nome_val = row.get("Nome Motorista") or row.get("Nome")
                sup_val = row.get("Cód.Supervisor Rota") or row.get("Supervisor Rota")
                status_val = str(row.get("Status")).strip() if pd.notnull(row.get("Status")) else "Ativo"
                
                if pd.notnull(cod_val):
                    try:
                        c_int = int(float(str(cod_val)))
                        if status_val.lower().startswith("ativo"):
                            mot_base_map[c_int] = {
                                "cpf": clean_cpf(str(cpf_val)) if pd.notnull(cpf_val) else "",
                                "name": str(nome_val).strip() if pd.notnull(nome_val) else "",
                                "supervisor_id": str(sup_val).strip() if pd.notnull(sup_val) else None,
                                "status": "Ativo"
                            }
                    except Exception:
                        pass
        except Exception as e:
            errors.append({"aba": "Base Mot", "colaborador": "Geral", "campo": "Estrutura", "problema": f"Erro na leitura da Base Mot: {str(e)}"})

    # 2. Base Aju Master Authority
    aju_base_map = {}
    if "Base Aju" in sheet_names:
        try:
            df_ba = pd.read_excel(xl, sheet_name="Base Aju")
            for _, row in df_ba.iterrows():
                cod_val = row.get("Codigo") or row.get("Cód")
                cpf_val = row.get("CPF")
                nome_val = row.get("Nome Ajudante") or row.get("Nome")
                sup_val = row.get("Supervisor Rota")
                status_val = str(row.get("Status")).strip() if pd.notnull(row.get("Status")) else "Ativo"

                if pd.notnull(cod_val):
                    try:
                        c_int = int(float(str(cod_val)))
                        if status_val.lower().startswith("ativo"):
                            aju_base_map[c_int] = {
                                "cpf": clean_cpf(str(cpf_val)) if pd.notnull(cpf_val) else "",
                                "name": str(nome_val).strip() if pd.notnull(nome_val) else "",
                                "supervisor_id": str(sup_val).strip() if pd.notnull(sup_val) else None,
                                "status": "Ativo"
                            }
                    except Exception:
                        pass
        except Exception as e:
            errors.append({"aba": "Base Aju", "colaborador": "Geral", "campo": "Estrutura", "problema": f"Erro na leitura da Base Aju: {str(e)}"})

    # Helper function to generate default 31 empty days for a month
    def generate_default_31_days(date_cols_list):
        days = []
        if date_cols_list:
            for c_idx, dt_str, d_num in date_cols_list:
                parts = dt_str.split("-")
                formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else dt_str
                days.append({
                    "day_num": d_num,
                    "date_str": formatted_date,
                    "rv_dia": 0.0,
                    "rv_acumulada": 0.0,
                    "caixas": 0.0,
                    "mapa": None,
                    "qtd_ajudantes": 1,
                    "hora_encerramento": "--:--",
                    "bateu_jl": "Sim",
                    "taxa_caixa": 0.10,
                    "jornada_status": "VERDE",
                    "devolucao_status": "VERDE",
                    "raio_status": "VERDE",
                    "status_dia": "SEM ROTA"
                })
        else:
            for d_num in range(1, 32):
                formatted_date = f"{str(d_num).zfill(2)}/07/2026"
                days.append({
                    "day_num": d_num,
                    "date_str": formatted_date,
                    "rv_dia": 0.0,
                    "rv_acumulada": 0.0,
                    "caixas": 0.0,
                    "mapa": None,
                    "qtd_ajudantes": 1,
                    "hora_encerramento": "--:--",
                    "bateu_jl": "Sim",
                    "taxa_caixa": 0.10,
                    "jornada_status": "VERDE",
                    "devolucao_status": "VERDE",
                    "raio_status": "VERDE",
                    "status_dia": "SEM ROTA"
                })
        return days

    # 3. Parse Motoristas Metrics & Daily Indicators from Consolidado RV MOT.
    mot_metrics_map = {}
    mot_daily_map = {}
    mot_date_cols = []

    if "Consolidado RV MOT." in sheet_names:
        df_mc = pd.read_excel(xl, sheet_name="Consolidado RV MOT.", header=None)
        
        # Map date columns in row 6
        row_dates = df_mc.iloc[6]
        for c_idx, val in enumerate(row_dates):
            if pd.notnull(val) and ("2026-" in str(val) or "202" in str(val)):
                dt_str = str(val)[:10]
                try:
                    d_num = int(dt_str.split("-")[2])
                except Exception:
                    d_num = len(mot_date_cols) + 1
                mot_date_cols.append((c_idx, dt_str, d_num))

        for idx in range(7, len(df_mc)):
            row = df_mc.iloc[idx]
            cod_cell = row[1]  # Col 2
            nome_cell = row[2] # Col 3
            
            if pd.isnull(cod_cell) or str(cod_cell).strip() == "":
                continue

            try:
                cod = int(float(str(cod_cell)))
            except ValueError:
                continue

            if cod in mot_metrics_map:
                continue

            rv_cx = float(row[4]) if pd.notnull(row[4]) and isinstance(row[4], (int, float)) else 0.0
            ad_raio = float(row[5]) if pd.notnull(row[5]) and isinstance(row[5], (int, float)) else 1.0
            devolucao = float(row[7]) if pd.notnull(row[7]) and isinstance(row[7], (int, float)) else 0.0
            bh_val = str(row[9]).strip() if pd.notnull(row[9]) else "00:00"
            he_val = float(row[11]) if pd.notnull(row[11]) and isinstance(row[11], (int, float)) else 0.0
            
            rv_total_raw = row[12]
            rv_prevista = 0.0
            if pd.notnull(rv_total_raw) and isinstance(rv_total_raw, (int, float)):
                rv_prevista = max(0.0, float(rv_total_raw))

            mot_metrics_map[cod] = {
                "rv_cx": rv_cx,
                "ad_raio": ad_raio,
                "devolucao": devolucao,
                "bh_val": bh_val,
                "he_val": he_val,
                "rv_prevista": rv_prevista,
                "nome_sheet": str(nome_cell).strip() if pd.notnull(nome_cell) else None
            }

            dev_st = "VERDE" if devolucao <= 0.02 else "VERMELHO"
            raio_st = "VERDE" if ad_raio >= 0.98 else ("AMARELO" if ad_raio >= 0.95 else "VERMELHO")

            # Parse daily indicator breakdown
            daily_list = []
            accum_rv = 0.0
            for c_idx, dt_str, d_num in mot_date_cols:
                rv_dia_val = row[c_idx] if c_idx < len(row) else 0.0
                rv_dia = float(rv_dia_val) if pd.notnull(rv_dia_val) and isinstance(rv_dia_val, (int, float)) else 0.0
                accum_rv += rv_dia

                mapa_val = row[c_idx + 1] if (c_idx + 1) < len(row) else ""
                aju_val = row[c_idx + 2] if (c_idx + 2) < len(row) else 1
                jornada_val = row[c_idx + 3] if (c_idx + 3) < len(row) else "--:--"
                jl_val = row[c_idx + 4] if (c_idx + 4) < len(row) else "Sim"
                caixas_val = row[c_idx + 5] if (c_idx + 5) < len(row) else 0.0

                mapa_str = str(mapa_val).strip() if pd.notnull(mapa_val) and str(mapa_val).strip() not in ["nan", "0", "0.0"] else None
                caixas = float(caixas_val) if pd.notnull(caixas_val) and isinstance(caixas_val, (int, float)) else 0.0
                
                try:
                    qtd_aju = int(float(str(aju_val))) if pd.notnull(aju_val) else 1
                except Exception:
                    qtd_aju = 1

                hora_enc = str(jornada_val).strip()[:5] if pd.notnull(jornada_val) and str(jornada_val).strip() not in ["nan", "00:00:00"] else "--:--"
                bateu_jl = "Sim" if str(jl_val).strip().lower() in ["sim", "s", "ok", "true", "1"] else "Não"
                jornada_status = "VERDE" if bateu_jl == "Sim" else "AMARELO"

                # Calculate exact rate per box according to Gestão RV_MOT rules
                if bateu_jl == "Sim":
                    taxa_caixa = 0.07 if qtd_aju >= 2 else 0.14
                else:
                    taxa_caixa = 0.05 if qtd_aju >= 2 else 0.10

                status_dia = "TRABALHADO" if (mapa_str or caixas > 0 or rv_dia > 0) else "SEM ROTA"

                parts = dt_str.split("-")
                formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else dt_str

                daily_list.append({
                    "day_num": d_num,
                    "date_str": formatted_date,
                    "rv_dia": round(rv_dia, 2),
                    "rv_acumulada": round(accum_rv, 2),
                    "caixas": round(caixas, 1),
                    "mapa": mapa_str,
                    "qtd_ajudantes": qtd_aju,
                    "hora_encerramento": hora_enc,
                    "bateu_jl": bateu_jl,
                    "taxa_caixa": taxa_caixa,
                    "jornada_status": jornada_status,
                    "devolucao_status": dev_st,
                    "raio_status": raio_st,
                    "status_dia": status_dia
                })
            mot_daily_map[cod] = daily_list
    else:
        errors.append({"aba": "Consolidado RV MOT.", "colaborador": "Geral", "campo": "Aba Ausente", "problema": "Aba 'Consolidado RV MOT.' não encontrada."})

    # 4. Parse Ajudantes Metrics & Daily Indicators from Consolidado RV AJU
    aju_metrics_map = {}
    aju_daily_map = {}
    aju_date_cols = []

    if "Consolidado RV AJU" in sheet_names:
        df_ac = pd.read_excel(xl, sheet_name="Consolidado RV AJU", header=None)

        # Map date columns in row 6
        row_dates = df_ac.iloc[6]
        for c_idx, val in enumerate(row_dates):
            if pd.notnull(val) and ("2026-" in str(val) or "202" in str(val)):
                dt_str = str(val)[:10]
                try:
                    d_num = int(dt_str.split("-")[2])
                except Exception:
                    d_num = len(aju_date_cols) + 1
                aju_date_cols.append((c_idx, dt_str, d_num))

        for idx in range(7, len(df_ac)):
            row = df_ac.iloc[idx]
            cod_cell = row[3]  # Col 4
            nome_cell = row[4] # Col 5
            
            if pd.isnull(cod_cell) or str(cod_cell).strip() == "":
                continue

            try:
                cod = int(float(str(cod_cell)))
            except ValueError:
                continue

            if cod in aju_metrics_map:
                continue

            rv_cx = float(row[6]) if pd.notnull(row[6]) and isinstance(row[6], (int, float)) else 0.0
            devolucao = float(row[7]) if pd.notnull(row[7]) and isinstance(row[7], (int, float)) else 0.0
            bh_val = str(row[9]).strip() if pd.notnull(row[9]) else "00:00"
            he_val = float(row[11]) if pd.notnull(row[11]) and isinstance(row[11], (int, float)) else 0.0
            
            rv_total_raw = row[12]
            rv_prevista = 0.0
            if pd.notnull(rv_total_raw) and isinstance(rv_total_raw, (int, float)):
                rv_prevista = max(0.0, float(rv_total_raw))

            aju_metrics_map[cod] = {
                "rv_cx": rv_cx,
                "devolucao": devolucao,
                "bh_val": bh_val,
                "he_val": he_val,
                "rv_prevista": rv_prevista,
                "nome_sheet": str(nome_cell).strip() if pd.notnull(nome_cell) else None
            }

            dev_st = "VERDE" if devolucao <= 0.02 else "VERMELHO"

            # Parse daily indicator breakdown
            daily_list = []
            accum_rv = 0.0
            for c_idx, dt_str, d_num in aju_date_cols:
                rv_dia_val = row[c_idx] if c_idx < len(row) else 0.0
                rv_dia = float(rv_dia_val) if pd.notnull(rv_dia_val) and isinstance(rv_dia_val, (int, float)) else 0.0
                accum_rv += rv_dia

                mapa_val = row[c_idx + 1] if (c_idx + 1) < len(row) else ""
                aju_val = row[c_idx + 2] if (c_idx + 2) < len(row) else 1
                jornada_val = row[c_idx + 3] if (c_idx + 3) < len(row) else "--:--"
                jl_val = row[c_idx + 4] if (c_idx + 4) < len(row) else "Sim"
                caixas_val = row[c_idx + 5] if (c_idx + 5) < len(row) else 0.0

                mapa_str = str(mapa_val).strip() if pd.notnull(mapa_val) and str(mapa_val).strip() not in ["nan", "0", "0.0"] else None
                caixas = float(caixas_val) if pd.notnull(caixas_val) and isinstance(caixas_val, (int, float)) else 0.0
                
                try:
                    qtd_aju = int(float(str(aju_val))) if pd.notnull(aju_val) else 1
                except Exception:
                    qtd_aju = 1

                hora_enc = str(jornada_val).strip()[:5] if pd.notnull(jornada_val) and str(jornada_val).strip() not in ["nan", "00:00:00"] else "--:--"
                bateu_jl = "Sim" if str(jl_val).strip().lower() in ["sim", "s", "ok", "true", "1"] else "Não"
                jornada_status = "VERDE" if bateu_jl == "Sim" else "AMARELO"

                # Calculate exact rate per box according to Gestão RV_AJU rules
                if bateu_jl == "Sim":
                    taxa_caixa = 0.07 if qtd_aju >= 2 else 0.14
                else:
                    taxa_caixa = 0.05 if qtd_aju >= 2 else 0.10

                status_dia = "TRABALHADO" if (mapa_str or caixas > 0 or rv_dia > 0) else "SEM ROTA"

                parts = dt_str.split("-")
                formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else dt_str

                daily_list.append({
                    "day_num": d_num,
                    "date_str": formatted_date,
                    "rv_dia": round(rv_dia, 2),
                    "rv_acumulada": round(accum_rv, 2),
                    "caixas": round(caixas, 1),
                    "mapa": mapa_str,
                    "qtd_ajudantes": qtd_aju,
                    "hora_encerramento": hora_enc,
                    "bateu_jl": bateu_jl,
                    "taxa_caixa": taxa_caixa,
                    "jornada_status": jornada_status,
                    "devolucao_status": dev_st,
                    "raio_status": "VERDE",
                    "status_dia": status_dia
                })
            aju_daily_map[cod] = daily_list
    else:
        errors.append({"aba": "Consolidado RV AJU", "colaborador": "Geral", "campo": "Aba Ausente", "problema": "Aba 'Consolidado RV AJU' não encontrada."})

    # Combine Base Mot + Base Aju + Consolidated Metrics & Daily
    records_to_process: List[Dict[str, Any]] = []

    # Process all Motoristas
    all_mot_codes = set(mot_base_map.keys()).union(set(mot_metrics_map.keys()))
    for cod in sorted(all_mot_codes):
        b_info = mot_base_map.get(cod, {})
        m_info = mot_metrics_map.get(cod, {})

        real_name = b_info.get("name") or m_info.get("nome_sheet")
        if not real_name:
            real_name = "NOME NÃO LOCALIZADO"
            errors.append({
                "aba": "Base Mot / Consolidado",
                "colaborador": f"Código {cod}",
                "campo": "Nome",
                "problema": f"Nome do Motorista código {cod} não foi localizado."
            })

        cpf = b_info.get("cpf") or f"333{str(cod).zfill(8)}"

        rv_prevista = m_info.get("rv_prevista", 0.0)
        rv_cx = m_info.get("rv_cx", 0.0)
        ad_raio = m_info.get("ad_raio", 1.0)
        devolucao = m_info.get("devolucao", 0.0)
        bh_val = m_info.get("bh_val", "00:00")
        he_cost = m_info.get("he_val", 0.0)

        dev_status = "VERDE" if devolucao <= 0.02 else "VERMELHO"
        raio_status = "VERDE" if ad_raio >= 0.98 else ("AMARELO" if ad_raio >= 0.95 else "VERMELHO")
        bh_status = "VERDE" if he_cost == 0 else "AMARELO"
        caixas_val = round(rv_cx * 15, 2) if rv_cx > 0 else 0.0

        daily_list = mot_daily_map.get(cod)
        if not daily_list or len(daily_list) == 0:
            daily_list = generate_default_31_days(mot_date_cols)

        records_to_process.append({
            "matricula": str(cod),
            "nome": real_name,
            "cpf": cpf,
            "cargo": "MOTORISTA",
            "supervisor_id": b_info.get("supervisor_id"),
            "rv_prevista": round(rv_prevista, 2),
            "rv_maxima": 1000.0,
            "rv_cx": round(rv_cx, 2),
            "ad_raio": ad_raio,
            "devolucao": devolucao,
            "bh": bh_val,
            "he_cost": round(he_cost, 2),
            "caixas_val": caixas_val,
            "dev_status": dev_status,
            "raio_status": raio_status,
            "bh_status": bh_status,
            "daily_list": daily_list
        })

    # Process all Ajudantes
    all_aju_codes = set(aju_base_map.keys()).union(set(aju_metrics_map.keys()))
    for cod in sorted(all_aju_codes):
        b_info = aju_base_map.get(cod, {})
        m_info = aju_metrics_map.get(cod, {})

        real_name = b_info.get("name") or m_info.get("nome_sheet")
        if not real_name:
            real_name = "NOME NÃO LOCALIZADO"
            errors.append({
                "aba": "Base Aju / Consolidado",
                "colaborador": f"Código {cod}",
                "campo": "Nome",
                "problema": f"Nome do Ajudante código {cod} não foi localizado."
            })

        cpf = b_info.get("cpf") or f"444{str(cod).zfill(8)}"

        rv_prevista = m_info.get("rv_prevista", 0.0)
        rv_cx = m_info.get("rv_cx", 0.0)
        devolucao = m_info.get("devolucao", 0.0)
        bh_val = m_info.get("bh_val", "00:00")
        he_cost = m_info.get("he_val", 0.0)

        dev_status = "VERDE" if devolucao <= 0.02 else "VERMELHO"
        bh_status = "VERDE" if he_cost == 0 else "AMARELO"
        caixas_val = round(rv_cx * 15, 2) if rv_cx > 0 else 0.0

        daily_list = aju_daily_map.get(cod)
        if not daily_list or len(daily_list) == 0:
            daily_list = generate_default_31_days(aju_date_cols)

        records_to_process.append({
            "matricula": str(cod),
            "nome": real_name,
            "cpf": cpf,
            "cargo": "AJUDANTE",
            "supervisor_id": b_info.get("supervisor_id"),
            "rv_prevista": round(rv_prevista, 2),
            "rv_maxima": 800.0,
            "rv_cx": round(rv_cx, 2),
            "ad_raio": 1.0,
            "devolucao": devolucao,
            "bh": bh_val,
            "he_cost": round(he_cost, 2),
            "caixas_val": caixas_val,
            "dev_status": dev_status,
            "raio_status": "VERDE",
            "bh_status": bh_status,
            "daily_list": daily_list
        })

    records_to_process.sort(key=lambda x: (x["rv_prevista"], x["nome"]), reverse=True)
    total_recs = len(records_to_process)
    
    sample_list = []
    has_unlocated_names = False

    for rank, rec in enumerate(records_to_process, 1):
        rec["ranking_pos"] = rank
        rec["ranking_total"] = total_recs
        
        ratio = (rec["rv_prevista"] / rec["rv_maxima"]) if rec["rv_maxima"] > 0 else 0.90
        perf = min(100.0, max(50.0, round(ratio * 100, 1)))
        rec["performance_pct"] = perf

        if rec["nome"] == "NOME NÃO LOCALIZADO":
            has_unlocated_names = True

        if len(sample_list) < 20:
            sample_list.append({
                "matricula": rec["matricula"],
                "nome": rec["nome"],
                "cargo": rec["cargo"],
                "masked_cpf": mask_cpf(rec["cpf"]),
                "performance_pct": rec["performance_pct"],
                "rv_prevista": rec["rv_prevista"],
                "rv_maxima": rec["rv_maxima"],
                "status": "VERDE" if rec["performance_pct"] >= 90 else ("AMARELO" if rec["performance_pct"] >= 75 else "VERMELHO"),
                "indicadores_count": 6
            })

    token = str(uuid.uuid4())
    PREVIEW_CACHE[token] = {
        "filename": filename,
        "competencia": competencia_input,
        "mot_count": len(all_mot_codes),
        "aju_count": len(all_aju_codes),
        "records": records_to_process,
        "errors": errors,
        "has_unlocated_names": has_unlocated_names
    }

    return {
        "competencia": competencia_input,
        "mot_found": len(all_mot_codes),
        "aju_found": len(all_aju_codes),
        "valid_count": total_recs if not has_unlocated_names else 0,
        "error_count": len(errors),
        "new_records": total_recs,
        "update_records": 0,
        "errors": errors,
        "sample": sample_list,
        "file_token": token
    }


def execute_import_confirm(file_token: str, db: Session, current_user_name: str) -> Dict[str, Any]:
    """
    Persists confirmed spreadsheet data and daily indicator records into SQLite database.
    """
    if file_token not in PREVIEW_CACHE:
        raise ValueError("Sessão de prévia expirada ou inválida. Por favor, envie a planilha novamente.")

    data = PREVIEW_CACHE[file_token]
    if data.get("has_unlocated_names") or data.get("errors"):
        critical_errs = [e for e in data["errors"] if e.get("campo") == "Nome"]
        if critical_errs:
            raise ValueError("Importação bloqueada: Existem colaboradores sem nome localizado nas bases mestre. Corrija o cadastro antes de importar.")

    data = PREVIEW_CACHE.pop(file_token)
    records = data["records"]
    competencia = data["competencia"]
    filename = data["filename"]

    created_count = 0
    updated_count = 0

    default_pass_hash = hash_password("jmb123")

    for rec in records:
        matricula = rec["matricula"]
        cpf = rec["cpf"]
        cargo = rec["cargo"]

        # Match user strictly by unique CPF first to avoid collisions between Motoristas and Ajudantes sharing the same code number!
        user = db.query(User).filter(User.cpf == cpf).first()
        if not user:
            user = db.query(User).filter(User.matricula == matricula, User.role == cargo).first()

        if not user:
            user = User(
                matricula=matricula,
                cpf=cpf,
                name=rec["nome"],
                role=cargo,
                password_hash=default_pass_hash,
                status="Ativo"
            )
            db.add(user)
            db.flush()
            created_count += 1
        else:
            user.name = rec["nome"]
            user.role = cargo
            user.matricula = matricula
            user.cpf = cpf
            db.flush()
            updated_count += 1

        perf = db.query(PerformanceRecord).filter(
            PerformanceRecord.user_id == user.id,
            PerformanceRecord.competencia == competencia
        ).first()

        if not perf:
            perf = PerformanceRecord(
                user_id=user.id,
                matricula=matricula,
                competencia=competencia,
                cargo=cargo
            )
            db.add(perf)

        perf.performance_pct = rec["performance_pct"]
        perf.rv_prevista = rec["rv_prevista"]
        perf.rv_maxima = rec["rv_maxima"]
        perf.ranking_pos = rec["ranking_pos"]
        perf.ranking_total = rec["ranking_total"]

        perf.caixas_val = rec["caixas_val"]
        perf.caixas_meta = 1000.0
        perf.caixas_pct = 100.0
        perf.caixas_status = "VERDE"

        perf.aderencia_raio_val = round(rec["ad_raio"] * 100, 1)
        perf.aderencia_raio_meta = 100.0
        perf.aderencia_raio_pct = round(rec["ad_raio"] * 100, 1)
        perf.aderencia_raio_status = rec["raio_status"]

        perf.devolucao_val = round(rec["devolucao"] * 100, 2)
        perf.devolucao_meta = 2.0
        perf.devolucao_pct = 100.0 if rec["devolucao"] <= 0.02 else 50.0
        perf.devolucao_status = rec["dev_status"]

        perf.banco_horas_val = rec["bh"]
        perf.banco_horas_meta = "20:00"
        perf.banco_horas_he_cost = rec["he_cost"]
        perf.banco_horas_status = rec["bh_status"]

        perf.ponto_val = "100%"
        perf.ponto_meta = "100%"
        perf.ponto_pct = 100.0
        perf.ponto_status = "VERDE"

        perf.jornada_val = "Conforme"
        perf.jornada_meta = "Conforme"
        perf.jornada_pct = 100.0
        perf.jornada_status = "VERDE"

        # Persist Daily Indicators Breakdown
        db.query(DailyPerformanceRecord).filter(
            DailyPerformanceRecord.user_id == user.id,
            DailyPerformanceRecord.competencia == competencia
        ).delete()

        for d_item in rec.get("daily_list", []):
            d_rec = DailyPerformanceRecord(
                user_id=user.id,
                matricula=matricula,
                competencia=competencia,
                date_str=d_item["date_str"],
                day_num=d_item["day_num"],
                rv_dia=d_item["rv_dia"],
                rv_acumulada=d_item["rv_acumulada"],
                caixas=d_item["caixas"],
                mapa=d_item["mapa"],
                qtd_ajudantes=d_item["qtd_ajudantes"],
                hora_encerramento=d_item["hora_encerramento"],
                bateu_jl=d_item["bateu_jl"],
                taxa_caixa=d_item.get("taxa_caixa", 0.10),
                jornada_status=d_item["jornada_status"],
                devolucao_status=d_item["devolucao_status"],
                raio_status=d_item["raio_status"],
                status_dia=d_item["status_dia"]
            )
            db.add(d_rec)

    history = ImportHistory(
        filename=filename,
        competencia=competencia,
        total_records=len(records),
        mot_count=data["mot_count"],
        aju_count=data["aju_count"],
        valid_count=len(records),
        error_count=len(data["errors"]),
        created_count=created_count,
        updated_count=updated_count,
        error_details_json=json.dumps(data["errors"]),
        imported_by_name=current_user_name
    )
    db.add(history)
    db.commit()

    return {
        "success": True,
        "message": f"Competência {competencia} atualizada com sucesso com indicadores diários!",
        "competencia": competencia,
        "total_processed": len(records),
        "created_users": created_count,
        "updated_users": updated_count
    }
