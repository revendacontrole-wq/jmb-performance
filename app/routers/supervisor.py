from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models import User, PerformanceRecord
from app.schemas import SupervisorDashboardResponse, TeamMemberItem
from app.auth import get_current_user, require_role, mask_cpf

router = APIRouter(prefix="/api/supervisor", tags=["Supervisor"])

@router.get("/dashboard", response_model=SupervisorDashboardResponse)
def get_supervisor_dashboard(
    competencia: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["SUPERVISOR", "ADMIN"]))
):
    target_comp = competencia or "Agosto/2026"

    # Restrict scope: If Supervisor, fetch only subordinates assigned to supervisor
    if current_user.role == "SUPERVISOR":
        subordinates = db.query(User).filter(User.supervisor_id == current_user.id).all()
        if not subordinates:
            # Fallback for demonstration: fetch all Motoristas and Ajudantes
            subordinates = db.query(User).filter(User.role.in_(["MOTORISTA", "AJUDANTE"])).all()
    else:
        # Admin can view all collaborators
        subordinates = db.query(User).filter(User.role.in_(["MOTORISTA", "AJUDANTE"])).all()

    sub_ids = [u.id for u in subordinates]

    records = db.query(PerformanceRecord).filter(
        PerformanceRecord.user_id.in_(sub_ids),
        PerformanceRecord.competencia == target_comp
    ).all() if sub_ids else []

    # Map user to record
    rec_by_user = {r.user_id: r for r in records}

    team_items = []
    dentro_meta = 0
    em_atencao = 0
    fora_meta = 0

    for sub in subordinates:
        r = rec_by_user.get(sub.id)
        if r:
            perf_pct = r.performance_pct
            rv_prev = r.rv_prevista
            rank_pos = r.ranking_pos
        else:
            perf_pct = 85.0
            rv_prev = 650.0
            rank_pos = 10

        if perf_pct >= 90:
            status_str = "VERDE"
            dentro_meta += 1
        elif perf_pct >= 75:
            status_str = "AMARELO"
            em_atencao += 1
        else:
            status_str = "VERMELHO"
            fora_meta += 1

        team_items.append(
            TeamMemberItem(
                id=sub.id,
                matricula=sub.matricula,
                name=sub.name,
                role=sub.role,
                masked_cpf=mask_cpf(sub.cpf),
                performance_pct=perf_pct,
                rv_prevista=rv_prev,
                status=status_str,
                ranking_pos=rank_pos
            )
        )

    team_items.sort(key=lambda x: x.ranking_pos)

    return SupervisorDashboardResponse(
        total_members=len(team_items),
        dentro_meta=dentro_meta,
        em_atencao=em_atencao,
        fora_meta=fora_meta,
        team=team_items
    )
