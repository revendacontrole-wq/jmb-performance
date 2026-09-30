from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.database import get_db
from app.models import User, PerformanceRecord, ImportHistory, ActionPlan, ExtraIndicatorRecord
from app.schemas import (
    PreviewResponse,
    ConfirmImportRequest,
    ImportConfirmResponse,
    ImportHistoryItem,
    UserSummary,
    UserCreateRequest,
    UserUpdateRequest,
    ActionPlanCreateRequest,
    ActionPlanItem
)
from app.auth import get_current_user, require_role, mask_cpf, clean_cpf, hash_password
from app.excel_engine import parse_excel_file, execute_import_confirm

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.post("/import/preview", response_model=PreviewResponse)
async def preview_excel_import(
    file: UploadFile = File(...),
    competencia: str = Form(...),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido. Por favor, envie uma planilha Excel (.xlsx ou .xls)."
        )

    try:
        contents = await file.read()
        preview_data = parse_excel_file(contents, file.filename, competencia)
        return preview_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Falha ao processar planilha: {str(e)}"
        )

@router.post("/import/confirm", response_model=ImportConfirmResponse)
def confirm_excel_import(
    data: ConfirmImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    try:
        result = execute_import_confirm(data.file_token, db, current_user.name)
        return result
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno ao gravar dados no banco: {str(e)}"
        )

@router.get("/import/history", response_model=List[ImportHistoryItem])
def get_import_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    history = db.query(ImportHistory).order_by(ImportHistory.imported_at.desc()).all()
    out = []
    for h in history:
        out.append(
            ImportHistoryItem(
                id=h.id,
                filename=h.filename,
                competencia=h.competencia,
                total_records=h.total_records,
                mot_count=h.mot_count,
                aju_count=h.aju_count,
                valid_count=h.valid_count,
                error_count=h.error_count,
                created_count=h.created_count,
                updated_count=h.updated_count,
                imported_by_name=h.imported_by_name,
                created_at=h.imported_at.strftime("%d/%m/%Y %H:%M") if h.imported_at else ""
            )
        )
    return out

@router.get("/collaborators", response_model=List[UserSummary])
def get_admin_collaborators(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    users = db.query(User).filter(User.role.in_(["MOTORISTA", "AJUDANTE", "SUPERVISOR"])).order_by(User.name.asc()).all()
    out = []
    for u in users:
        out.append(
            UserSummary(
                id=u.id,
                matricula=u.matricula or "-",
                name=u.name,
                role=u.role,
                masked_cpf=mask_cpf(u.cpf),
                status=u.status
            )
        )
    return out

@router.post("/collaborators", response_model=UserSummary)
def create_collaborator(
    data: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    c_cpf = clean_cpf(data.cpf)
    if not c_cpf or len(c_cpf) < 11:
        raise HTTPException(status_code=400, detail="CPF inválido. Por favor insira 11 dígitos numéricos.")

    existing_cpf = db.query(User).filter(User.cpf == c_cpf).first()
    if existing_cpf:
        raise HTTPException(status_code=400, detail=f"Já existe um colaborador cadastrado com o CPF {data.cpf}.")

    pass_hash = hash_password(data.password or "123")
    user = User(
        name=data.name.strip(),
        matricula=data.matricula.strip(),
        cpf=c_cpf,
        role=data.role.upper(),
        password_hash=pass_hash,
        supervisor_id=data.supervisor_id,
        status=data.status or "Ativo"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserSummary(
        id=user.id,
        matricula=user.matricula or "-",
        name=user.name,
        role=user.role,
        masked_cpf=mask_cpf(user.cpf),
        status=user.status
    )

@router.put("/collaborators/{user_id}", response_model=UserSummary)
def update_collaborator(
    user_id: int,
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    if data.name:
        user.name = data.name.strip()
    if data.matricula:
        user.matricula = data.matricula.strip()
    if data.cpf:
        c_cpf = clean_cpf(data.cpf)
        if c_cpf:
            user.cpf = c_cpf
    if data.role:
        user.role = data.role.upper()
    if data.password:
        user.password_hash = hash_password(data.password)
    if data.status:
        user.status = data.status

    db.commit()
    db.refresh(user)

    return UserSummary(
        id=user.id,
        matricula=user.matricula or "-",
        name=user.name,
        role=user.role,
        masked_cpf=mask_cpf(user.cpf),
        status=user.status
    )

@router.delete("/collaborators/{user_id}")
def delete_collaborator(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    user.status = "Inativo"
    db.commit()
    return {"success": True, "message": f"Colaborador {user.name} desativado com sucesso."}


@router.get("/managerial-overview")
def get_managerial_overview(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    all_comps = [c[0] for c in db.query(PerformanceRecord.competencia).distinct().all() if c[0]]
    target_comp = competencia if competencia else (all_comps[0] if all_comps else "Julho/2026")

    records = db.query(PerformanceRecord).filter(PerformanceRecord.competencia == target_comp).all()
    
    total_collabs = len(records)
    avg_perf = round(sum(r.performance_pct for r in records) / total_collabs, 1) if total_collabs > 0 else 0.0
    total_rv = round(sum(r.rv_prevista for r in records), 2)
    
    avg_devolucao = round(sum(r.devolucao_val or 0.0 for r in records) / total_collabs, 2) if total_collabs > 0 else 0.0
    avg_raio = round(sum(r.aderencia_raio_val or 100.0 for r in records) / total_collabs, 1) if total_collabs > 0 else 100.0
    total_he_cost = round(sum(r.banco_horas_he_cost or 0.0 for r in records), 2)
    total_caixas = round(sum(r.caixas_val or 0.0 for r in records), 1)

    # Extra Indicators aggregated
    extra_recs = db.query(ExtraIndicatorRecord).filter(ExtraIndicatorRecord.competencia == target_comp).all()
    total_mapas = sum(e.mapas or 0 for e in extra_recs)
    total_entregas = sum(e.entregas or 0 for e in extra_recs)
    avg_reposicao_pct = round(sum(e.reposicao_pct or 0.0 for e in extra_recs) / len(extra_recs), 1) if extra_recs else 0.0

    dentro_meta = sum(1 for r in records if r.performance_pct >= 90)
    em_atencao = sum(1 for r in records if 75 <= r.performance_pct < 90)
    fora_meta = sum(1 for r in records if r.performance_pct < 75)

    plans_count = db.query(ActionPlan).filter(ActionPlan.competencia == target_comp).count()
    open_plans_count = db.query(ActionPlan).filter(ActionPlan.competencia == target_comp, ActionPlan.status != "Concluído").count()

    # Full Collaborator Table for Managerial Overview (Consolidando todos os 10+ indicadores)
    extra_by_user = {e.user_id: e for e in extra_recs}
    all_collabs_detail = []
    
    for r in sorted(records, key=lambda x: x.ranking_pos or 999):
        u = db.query(User).filter(User.id == r.user_id).first()
        ex = extra_by_user.get(r.user_id)
        all_collabs_detail.append({
            "id": r.user_id,
            "nome": u.name if u else "Colaborador",
            "matricula": u.matricula if u else "-",
            "role": r.cargo,
            "performance_pct": r.performance_pct,
            "rating": r.rating or "Rating B",
            "rv_prevista": r.rv_prevista,
            "caixas_val": r.caixas_val or 0.0,
            "devolucao_val": f"{(r.devolucao_val or 0.0):.2f}%",
            "aderencia_raio_val": f"{(r.aderencia_raio_val or 100.0):.1f}%",
            "banco_horas_val": r.banco_horas_val or "00:00",
            "he_cost": r.banco_horas_he_cost or 0.0,
            "mapas": ex.mapas if ex else 0,
            "entregas": ex.entregas if ex else 0,
            "reposicao_pct": f"{(ex.reposicao_pct if ex else 0.0):.1f}%",
            "status": "VERDE" if r.performance_pct >= 90 else ("AMARELO" if r.performance_pct >= 75 else "VERMELHO")
        })

    at_risk = [c for c in all_collabs_detail if c["performance_pct"] < 90]

    return {
        "admin_name": current_user.name,
        "competencia": target_comp,
        "available_competencias": all_comps or [target_comp],
        "total_collabs": total_collabs,
        "avg_perf": avg_perf,
        "total_rv": total_rv,
        "avg_devolucao": avg_devolucao,
        "avg_raio": avg_raio,
        "total_he_cost": total_he_cost,
        "total_caixas": total_caixas,
        "total_mapas": total_mapas,
        "total_entregas": total_entregas,
        "avg_reposicao_pct": avg_reposicao_pct,
        "dentro_meta": dentro_meta,
        "em_atencao": em_atencao,
        "fora_meta": fora_meta,
        "plans_count": plans_count,
        "open_plans_count": open_plans_count,
        "at_risk_collaborators": at_risk,
        "all_collaborators": all_collabs_detail
    }

@router.get("/action-plans", response_model=List[ActionPlanItem])
def get_action_plans(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    query = db.query(ActionPlan)
    if competencia:
        query = query.filter(ActionPlan.competencia == competencia)
    plans = query.order_by(ActionPlan.created_at.desc()).all()
    
    out = []
    for p in plans:
        out.append(ActionPlanItem(
            id=p.id,
            user_id=p.user_id,
            collaborator_name=p.collaborator_name,
            role=p.role,
            competencia=p.competencia,
            issue_description=p.issue_description,
            action_title=p.action_title,
            corrective_measure=p.corrective_measure,
            deadline=p.deadline,
            responsible_name=p.responsible_name,
            status=p.status,
            created_at=p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else ""
        ))
    return out

@router.post("/action-plans", response_model=ActionPlanItem)
def create_action_plan(
    data: ActionPlanCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    plan = ActionPlan(
        user_id=user.id,
        collaborator_name=user.name,
        role=user.role,
        competencia=data.competencia,
        issue_description=data.issue_description.strip(),
        action_title=data.action_title.strip(),
        corrective_measure=data.corrective_measure.strip(),
        deadline=data.deadline.strip(),
        responsible_name=current_user.name,
        status="Pendente"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return ActionPlanItem(
        id=plan.id,
        user_id=plan.user_id,
        collaborator_name=plan.collaborator_name,
        role=plan.role,
        competencia=plan.competencia,
        issue_description=plan.issue_description,
        action_title=plan.action_title,
        corrective_measure=plan.corrective_measure,
        deadline=plan.deadline,
        responsible_name=plan.responsible_name,
        status=plan.status,
        created_at=plan.created_at.strftime("%d/%m/%Y %H:%M") if plan.created_at else ""
    )

@router.put("/action-plans/{plan_id}/status")
def update_action_plan_status(
    plan_id: int,
    status_val: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN", "SUPERVISOR"]))
):
    plan = db.query(ActionPlan).filter(ActionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plano de Ação não encontrado.")

    plan.status = status_val
    db.commit()
    return {"success": True, "message": f"Status do Plano de Ação alterado para {status_val}."}

