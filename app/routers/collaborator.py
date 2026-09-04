from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.database import get_db
from app.models import User, PerformanceRecord, DailyPerformanceRecord
from app.schemas import (
    CollaboratorDashboardResponse,
    IndicatorItem,
    ResultBreakdown,
    HistoryItem
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/collaborator", tags=["Collaborator"])

@router.get("/dashboard", response_model=CollaboratorDashboardResponse)
def get_collaborator_dashboard(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    # Fetch all stored competencies for user
    records = db.query(PerformanceRecord).filter(PerformanceRecord.user_id == current_user.id).order_by(PerformanceRecord.created_at.desc()).all()
    
    if not records:
        available_competencias = ["Julho/2026"]
        target_comp = competencia or "Julho/2026"
        perf = PerformanceRecord(
            user_id=current_user.id,
            matricula=current_user.matricula or "000",
            competencia=target_comp,
            cargo=current_user.role,
            performance_pct=90.0,
            rv_prevista=750.0,
            rv_maxima=1000.0 if current_user.role == "MOTORISTA" else 800.0,
            ranking_pos=1,
            ranking_total=1
        )
    else:
        available_competencias = list(dict.fromkeys([r.competencia for r in records]))
        if competencia:
            perf = next((r for r in records if r.competencia == competencia), records[0])
        else:
            perf = records[0]

    # Build 6 Indicator Items
    indicators = [
        IndicatorItem(
            key="devolucao",
            label="Devolução",
            current_val=f"{perf.devolucao_val:.2f}%",
            meta_val=f"≤ {perf.devolucao_meta:.2f}%",
            pct=perf.devolucao_pct,
            status=perf.devolucao_status,
            impact_note="Premiação R$ 70,00 mantida" if perf.devolucao_status == "VERDE" else "Devolução acima da meta reduziu bônus"
        ),
        IndicatorItem(
            key="aderencia_raio",
            label="Aderência ao Raio",
            current_val=f"{perf.aderencia_raio_val:.1f}%",
            meta_val=f"≥ {perf.aderencia_raio_meta:.0f}%",
            pct=perf.aderencia_raio_pct,
            status=perf.aderencia_raio_status,
            impact_note="Superou meta de geolocalização" if perf.aderencia_raio_status == "VERDE" else "Abaixo do raio de entregas"
        ),
        IndicatorItem(
            key="banco_horas",
            label="Banco de Horas",
            current_val=perf.banco_horas_val,
            meta_val=f"≤ {perf.banco_horas_meta}",
            pct=100.0 if perf.banco_horas_status == "VERDE" else 75.0,
            status=perf.banco_horas_status,
            impact_note="Sem descontos de HE" if perf.banco_horas_he_cost == 0 else f"Desconto HE: R$ {perf.banco_horas_he_cost:.2f}"
        ),
        IndicatorItem(
            key="jornada",
            label="Jornada",
            current_val=perf.jornada_val,
            meta_val=perf.jornada_meta,
            pct=perf.jornada_pct,
            status=perf.jornada_status,
            impact_note="Jornada dentro da janela limite"
        ),
        IndicatorItem(
            key="caixas",
            label="Caixas Entregues",
            current_val=f"{perf.caixas_val:.0f} cx",
            meta_val=f"{perf.caixas_meta:.0f} cx",
            pct=perf.caixas_pct,
            status=perf.caixas_status,
            impact_note="Volume de entrega computado na RV Bruta"
        ),
        IndicatorItem(
            key="ponto",
            label="Batida de Ponto",
            current_val=perf.ponto_val,
            meta_val=perf.ponto_meta,
            pct=perf.ponto_pct,
            status=perf.ponto_status,
            impact_note="Marcações de ponto 100% validadas"
        )
    ]

    dentro_meta = [ind.label for ind in indicators if ind.status == "VERDE"]
    fora_meta = [ind.label for ind in indicators if ind.status in ["AMARELO", "VERMELHO"]]
    
    fatores_reducao = []
    if perf.devolucao_status != "VERDE":
        fatores_reducao.append(f"Devolução de {perf.devolucao_val:.2f}% acima da meta de 2.0%")
    if perf.aderencia_raio_status != "VERDE" and perf.cargo == "MOTORISTA":
        fatores_reducao.append(f"Aderência ao Raio de {perf.aderencia_raio_val:.1f}% abaixo dos 100%")
    if perf.banco_horas_he_cost > 0:
        fatores_reducao.append(f"Abatimento de R$ {perf.banco_horas_he_cost:.2f} por excesso de Hora Extra")
    if not fatores_reducao:
        fatores_reducao.append("Nenhum fator de redução significativo registrado no mês.")

    potencial_restante = max(0.0, round(perf.rv_maxima - perf.rv_prevista, 2))

    breakdown = ResultBreakdown(
        dentro_meta=dentro_meta,
        fora_meta=fora_meta,
        fatores_reducao=fatores_reducao,
        potencial_restante=potencial_restante,
        rv_prevista=perf.rv_prevista,
        rv_maxima=perf.rv_maxima
    )

    return CollaboratorDashboardResponse(
        name=current_user.name,
        competencia=perf.competencia,
        performance_pct=perf.performance_pct,
        rv_prevista=perf.rv_prevista,
        rv_maxima=perf.rv_maxima,
        ranking_pos=perf.ranking_pos,
        ranking_total=perf.ranking_total,
        indicators=indicators,
        breakdown=breakdown,
        available_competencias=available_competencias
    )

@router.get("/daily", response_model=List[Dict[str, Any]])
def get_collaborator_daily(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    comp_target = competencia or "Julho/2026"
    records = db.query(DailyPerformanceRecord).filter(
        DailyPerformanceRecord.user_id == current_user.id,
        DailyPerformanceRecord.competencia == comp_target
    ).order_by(DailyPerformanceRecord.day_num.asc()).all()

    if not records:
        # Fallback 31-day calendar structure for users without specific daily records
        out = []
        for d in range(1, 32):
            out.append({
                "day_num": d,
                "date_str": f"{str(d).zfill(2)}/07/2026",
                "rv_dia": 0.0,
                "rv_acumulada": 0.0,
                "caixas": 0.0,
                "mapa": "-",
                "qtd_ajudantes": 1,
                "hora_encerramento": "--:--",
                "bateu_jl": "Sim",
                "taxa_caixa": 0.10,
                "jornada_status": "VERDE",
                "devolucao_status": "VERDE",
                "raio_status": "VERDE",
                "status_dia": "SEM ROTA"
            })
        return out

    out = []
    for r in records:
        out.append({
            "day_num": r.day_num,
            "date_str": r.date_str,
            "rv_dia": r.rv_dia,
            "rv_acumulada": r.rv_acumulada,
            "caixas": r.caixas,
            "mapa": r.mapa or "-",
            "qtd_ajudantes": r.qtd_ajudantes or 1,
            "hora_encerramento": r.hora_encerramento or "--:--",
            "bateu_jl": r.bateu_jl or "Sim",
            "taxa_caixa": r.taxa_caixa or 0.10,
            "jornada_status": r.jornada_status or "VERDE",
            "devolucao_status": r.devolucao_status or "VERDE",
            "raio_status": r.raio_status or "VERDE",
            "status_dia": r.status_dia or "TRABALHADO"
        })
    return out

@router.get("/history", response_model=List[HistoryItem])
def get_collaborator_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    records = db.query(PerformanceRecord).filter(PerformanceRecord.user_id == current_user.id).order_by(PerformanceRecord.created_at.asc()).all()
    
    if not records:
        return [
            HistoryItem(
                competencia="Julho/2026",
                performance_pct=94.0,
                rv_prevista=842.50,
                ranking_pos=6,
                status_geral="VERDE"
            )
        ]

    history = []
    for r in records:
        status_geral = "VERDE" if r.performance_pct >= 90 else ("AMARELO" if r.performance_pct >= 75 else "VERMELHO")
        history.append(
            HistoryItem(
                competencia=r.competencia,
                performance_pct=r.performance_pct,
                rv_prevista=r.rv_prevista,
                ranking_pos=r.ranking_pos,
                status_geral=status_geral
            )
        )
    return history
