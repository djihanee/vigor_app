from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import progress_service as service
import schemas
from deps import get_current_user, get_db   # <- adapt to your project (see notes)
from models import User, Workout
router = APIRouter(prefix="/progress", tags=["Progress"])
@router.get("", response_model=schemas.ProgressOut)
def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One call that feeds the whole Progress screen."""
    return service.full_progress(db, current_user.id)
@router.get("/calories", response_model=schemas.CaloriesOut)
def get_calories(
    week_offset: int = 0,   # 0 = this week, -1 = last week
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if week_offset > 0:
        raise HTTPException(status_code=400, detail="week_offset must be 0 or negative")
    return service.calories_for_week(db, current_user.id, week_offset)
@router.get("/summary", response_model=schemas.SummaryOut)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.summary(db, current_user.id)
@router.get("/weight-trend", response_model=schemas.WeightTrendOut)
def get_weight_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    days = min(max(days, 7), 365)
    return service.weight_trend(db, current_user.id, days)
@router.get("/consistency", response_model=schemas.ConsistencyOut)
def get_consistency(
    week_offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if week_offset > 0:
        raise HTTPException(status_code=400, detail="week_offset must be 0 or negative")
    return service.consistency(db, current_user.id, week_offset)
@router.post("/workouts", status_code=201)
def log_workout(
    body: schemas.WorkoutIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a workout. Needed so the page has data. Move it to activity.py if you prefer."""
    workout = Workout(
        user_id=current_user.id,
        calories_burned=body.calories_burned,
        duration_min=body.duration_min,
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    return {"id": workout.id}
 