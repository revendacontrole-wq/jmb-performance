import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models import User, Training
from app.schemas import TrainingItem
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/trainings", tags=["Trainings"])

import base64
import mimetypes
from fastapi.responses import Response

def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"

@router.get("", response_model=List[TrainingItem])
def get_all_trainings(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    query = db.query(Training)
    if category and category.lower() != "todas":
        query = query.filter(Training.category == category)
        
    trainings = query.order_by(Training.created_at.desc()).all()

    out = []
    for tr in trainings:
        file_url = tr.file_url if tr.file_url else f"/api/trainings/{tr.id}/download"
        out.append(
            TrainingItem(
                id=tr.id,
                title=tr.title,
                description=tr.description or "",
                category=tr.category,
                file_filename=tr.file_filename,
                file_url=file_url,
                file_size_formatted=format_file_size(tr.file_size_bytes or 0),
                uploaded_by_name=tr.uploaded_by_name,
                created_at=tr.created_at.strftime("%d/%m/%Y %H:%M") if tr.created_at else ""
            )
        )
    return out

@router.get("/{training_id}/download")
def download_training_file(
    training_id: int,
    db: Session = Depends(get_db)
):
    tr = db.query(Training).filter(Training.id == training_id).first()
    if not tr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material não encontrado.")

    if not tr.file_data_base64:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo do arquivo não está disponível no banco.")

    try:
        file_bytes = base64.b64decode(tr.file_data_base64)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao decodificar o arquivo.")

    mime_type, _ = mimetypes.guess_type(tr.file_filename)
    if not mime_type:
        mime_type = "application/pdf" if tr.file_filename.lower().endswith(".pdf") else "application/octet-stream"

    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{tr.file_filename}"'
        }
    )

@router.post("", response_model=TrainingItem)
async def upload_training(
    payload: Optional[TrainingCreateRequest] = None,
    title: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file_url_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    try:
        req_title = None
        req_cat = "Procedimentos Operacionais"
        req_desc = ""
        req_filename = "Documento / Link"
        req_file_url = ""
        b64_str = None
        file_size = 0

        if payload:
            req_title = payload.title
            req_cat = payload.category or "Procedimentos Operacionais"
            req_desc = payload.description or ""
            if payload.file_url and payload.file_url.strip():
                req_file_url = payload.file_url.strip()
                req_filename = payload.filename or "Link do Documento / Vídeo"
            elif payload.file_b64 and payload.file_b64.strip():
                req_filename = payload.filename or "arquivo"
                b64_str = payload.file_b64.strip()
                if "," in b64_str:
                    b64_str = b64_str.split(",")[-1]
                file_bytes = base64.b64decode(b64_str)
                file_size = len(file_bytes)
        elif title:
            req_title = title
            req_cat = category or "Procedimentos Operacionais"
            req_desc = description or ""
            if file_url_input and file_url_input.strip():
                req_file_url = file_url_input.strip()
                req_filename = "Link do Documento / Vídeo"
            elif file:
                req_filename = file.filename
                file_bytes = await file.read()
                file_size = len(file_bytes)
                b64_str = base64.b64encode(file_bytes).decode('utf-8')

        if not req_title or len(req_title.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Por favor, digite um título válido para o treinamento."
            )

        if not req_file_url and not b64_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Por favor, informe o Link do Documento/Vídeo ou selecione um Arquivo de até 2.0 MB para anexar."
            )

        if b64_str and file_size > 2.5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo enviado é muito grande para upload direto no servidor (máximo 2.0 MB). Por favor, insira o Link do documento (Google Drive / OneDrive / Canva) ou comprima o PDF."
            )

        tr = Training(
            title=req_title.strip(),
            description=req_desc.strip() if req_desc else "",
            category=req_cat.strip() if req_cat else "Procedimentos Operacionais",
            file_filename=req_filename,
            file_url=req_file_url,
            file_size_bytes=file_size,
            file_data_base64=b64_str if b64_str else None,
            uploaded_by_name=current_user.name
        )
        db.add(tr)
        db.commit()
        db.refresh(tr)

        if not req_file_url:
            tr.file_url = f"/api/trainings/{tr.id}/download"
            db.commit()

        size_formatted = "Link Externo" if req_file_url else format_file_size(tr.file_size_bytes)

        return TrainingItem(
            id=tr.id,
            title=tr.title,
            description=tr.description or "",
            category=tr.category,
            file_filename=tr.file_filename,
            file_url=tr.file_url,
            file_size_formatted=size_formatted,
            uploaded_by_name=tr.uploaded_by_name,
            created_at=tr.created_at.strftime("%d/%m/%Y %H:%M") if tr.created_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar material: {str(e)}"
        )

@router.delete("/{training_id}")
def delete_training(
    training_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    tr = db.query(Training).filter(Training.id == training_id).first()
    if not tr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Treinamento não localizado."
        )

    db.delete(tr)
    db.commit()

    return {"success": True, "message": "Treinamento removido com sucesso."}
