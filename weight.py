from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from deps import get_current_user
from models import User, WeightLog
from schemas import WeightIn, WeightOut, WeightSummary
router = APIRouter(prefix="/users/me/weight", tags=["weight"])
@router.put("", response_model=WeightOut)
def set_weight(
    data: WeightIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.weight_kg = data.weight_kg
    log = WeightLog(user_id=current_user.id, weight_kg=data.weight_kg)
    db.add(log)
    db.commit()
    db.refresh(log)
    return WeightOut(weight_kg=log.weight_kg, logged_at=log.logged_at)
@router.get("", response_model=WeightOut)
def get_weight(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    last = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == current_user.id)
        .order_by(WeightLog.logged_at.desc())
        .first()
    )
    if last is None:
        return WeightOut(weight_kg=current_user.weight_kg or 60.0, logged_at=datetime.utcnow())
    return WeightOut(weight_kg=last.weight_kg, logged_at=last.logged_at)


@router.get("/history", response_model=WeightSummary)
def weight_history(
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == current_user.id)
        .order_by(WeightLog.logged_at.asc())
        .all()
    )
    if not rows:
        return WeightSummary(current=None, start=None, change=None, history=[])

    start, current = rows[0].weight_kg, rows[-1].weight_kg
    history = [WeightOut(weight_kg=r.weight_kg, logged_at=r.logged_at) for r in rows[-limit:]]
    return WeightSummary(
        current=current,
        start=start,
        change=round(current - start, 1),
        history=history,
    )