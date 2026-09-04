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

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "uploads", "trainings")
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
        out.append(
            TrainingItem(
                id=tr.id,
                title=tr.title,
                description=tr.description or "",
                category=tr.category,
                file_filename=tr.file_filename,
                file_url=tr.file_url,
                file_size_formatted=format_file_size(tr.file_size_bytes or 0),
                uploaded_by_name=tr.uploaded_by_name,
                created_at=tr.created_at.strftime("%d/%m/%Y %H:%M") if tr.created_at else ""
            )
        )
    return out

@router.post("", response_model=TrainingItem)
async def upload_training(
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    if not title or len(title.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por favor, digite um título válido para o treinamento."
        )

    # Save uploaded file to static/uploads/trainings/
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1].lower()
    
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    file_bytes = await file.read()
    file_size = len(file_bytes)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    file_url = f"/static/uploads/trainings/{unique_filename}"

    tr = Training(
        title=title.strip(),
        description=description.strip() if description else "",
        category=category.strip(),
        file_filename=original_filename,
        file_url=file_url,
        file_size_bytes=file_size,
        uploaded_by_name=current_user.name
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)

    return TrainingItem(
        id=tr.id,
        title=tr.title,
        description=tr.description or "",
        category=tr.category,
        file_filename=tr.file_filename,
        file_url=tr.file_url,
        file_size_formatted=format_file_size(tr.file_size_bytes),
        uploaded_by_name=tr.uploaded_by_name,
        created_at=tr.created_at.strftime("%d/%m/%Y %H:%M") if tr.created_at else ""
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

    # Try removing physical file
    if tr.file_url.startswith("/static/uploads/trainings/"):
        fname = os.path.basename(tr.file_url)
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
            except Exception:
                pass

    db.delete(tr)
    db.commit()

    return {"success": True, "message": "Treinamento removido com sucesso."}
