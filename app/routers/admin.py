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
    UserSummary
)
from app.auth import get_current_user, require_role, mask_cpf
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
    current_user: User = Depends(require_role(["ADMIN"]))
):
    users = db.query(User).filter(User.role.in_(["MOTORISTA", "AJUDANTE"])).order_by(User.name.asc()).all()
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
