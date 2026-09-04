from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models import User, Feedback
from app.schemas import (
    FeedbackCreateRequest,
    FeedbackItem,
    FeedbackStatusUpdateRequest
)
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

@router.post("", response_model=FeedbackItem)
def submit_feedback(
    data: FeedbackCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    if not data.comment or len(data.comment.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Por favor, digite um comentário com pelo menos 5 caracteres."
        )

    fb = Feedback(
        user_id=current_user.id,
        matricula=current_user.matricula or "-",
        user_name=current_user.name,
        user_role=current_user.role,
        competencia=data.competencia.strip(),
        incident_date=data.incident_date.strip(),
        category=data.category.strip(),
        comment=data.comment.strip(),
        status="PENDENTE"
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    return FeedbackItem(
        id=fb.id,
        user_id=fb.user_id,
        matricula=fb.matricula,
        user_name=fb.user_name,
        user_role=fb.user_role,
        competencia=fb.competencia,
        incident_date=fb.incident_date,
        category=fb.category,
        comment=fb.comment,
        status=fb.status,
        admin_notes=fb.admin_notes,
        created_at=fb.created_at.strftime("%d/%m/%Y %H:%M") if fb.created_at else ""
    )

@router.get("/my", response_model=List[FeedbackItem])
def get_my_feedbacks(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["MOTORISTA", "AJUDANTE", "SUPERVISOR", "ADMIN"]))
):
    query = db.query(Feedback).filter(Feedback.user_id == current_user.id)
    if competencia:
        query = query.filter(Feedback.competencia == competencia)
    feedbacks = query.order_by(Feedback.created_at.desc()).all()

    out = []
    for fb in feedbacks:
        out.append(
            FeedbackItem(
                id=fb.id,
                user_id=fb.user_id,
                matricula=fb.matricula,
                user_name=fb.user_name,
                user_role=fb.user_role,
                competencia=fb.competencia,
                incident_date=fb.incident_date,
                category=fb.category,
                comment=fb.comment,
                status=fb.status,
                admin_notes=fb.admin_notes,
                created_at=fb.created_at.strftime("%d/%m/%Y %H:%M") if fb.created_at else ""
            )
        )
    return out

@router.get("/all", response_model=List[FeedbackItem])
def get_all_feedbacks(
    status_filter: Optional[str] = Query(None),
    category_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "ADMIN"]))
):
    query = db.query(Feedback)
    if status_filter and status_filter.lower() != "todos":
        query = query.filter(Feedback.status == status_filter)
    if category_filter and category_filter.lower() != "todas":
        query = query.filter(Feedback.category == category_filter)
        
    feedbacks = query.order_by(Feedback.created_at.desc()).all()

    out = []
    for fb in feedbacks:
        out.append(
            FeedbackItem(
                id=fb.id,
                user_id=fb.user_id,
                matricula=fb.matricula,
                user_name=fb.user_name,
                user_role=fb.user_role,
                competencia=fb.competencia,
                incident_date=fb.incident_date,
                category=fb.category,
                comment=fb.comment,
                status=fb.status,
                admin_notes=fb.admin_notes,
                created_at=fb.created_at.strftime("%d/%m/%Y %H:%M") if fb.created_at else ""
            )
        )
    return out

@router.put("/{feedback_id}/status", response_model=FeedbackItem)
def update_feedback_status(
    feedback_id: int,
    data: FeedbackStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "ADMIN"]))
):
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback não localizado."
        )

    fb.status = data.status
    if data.admin_notes is not None:
        fb.admin_notes = data.admin_notes
    db.commit()
    db.refresh(fb)

    return FeedbackItem(
        id=fb.id,
        user_id=fb.user_id,
        matricula=fb.matricula,
        user_name=fb.user_name,
        user_role=fb.user_role,
        competencia=fb.competencia,
        incident_date=fb.incident_date,
        category=fb.category,
        comment=fb.comment,
        status=fb.status,
        admin_notes=fb.admin_notes,
        created_at=fb.created_at.strftime("%d/%m/%Y %H:%M") if fb.created_at else ""
    )
