from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import User, Campaign
from app.auth import get_current_user, require_role

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.get("")
def get_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return campaigns

@router.post("")
def create_campaign(
    title: str,
    period: str,
    goal: str,
    prize: str,
    progress_pct: float = 0.0,
    status: str = "Em Andamento",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["ADMIN"]))
):
    c = Campaign(
        title=title,
        period=period,
        goal=goal,
        prize=prize,
        progress_pct=progress_pct,
        status=status
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
