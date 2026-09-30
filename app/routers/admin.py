from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.database import get_db
from app.models import User, PerformanceRecord, ImportHistory
from app.schemas import (
    PreviewResponse,
    ConfirmImportRequest,
    ImportConfirmResponse,
    ImportHistoryItem,
    UserSummary,
    UserCreateRequest,
    UserUpdateRequest
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

