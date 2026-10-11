from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import home_service as service
import schemas
from deps import get_current_user, get_db   # <- adapt to your project
from models import User
router = APIRouter(prefix="/home", tags=["Home"])
@router.get("", response_model=schemas.HomeOut)
def get_home(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feeds the whole Home screen in one call."""
    return service.build_home(db, current_user)
# ---------------------------------------------------------------- logging
@router.post("/water", status_code=201)
def add_water(
    body: schemas.WaterIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"water_ml": service.log_water(db, current_user.id, body.amount_ml)}
@router.put("/steps")
def update_steps(
    body: schemas.StepsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"steps": service.set_steps(db, current_user.id, body.steps)}
@router.put("/sleep")
def update_sleep(
    body: schemas.SleepIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"sleep_minutes": service.set_sleep(db, current_user.id, body.minutes)}
@router.post("/food", status_code=201)
def add_food(
    body: schemas.FoodIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return {"calories_eaten_today": service.log_food(db, current_user.id, body)}
 
 
# ---------------------------------------------------------------- workout plans ("see all")
@router.get("/workout-plans", response_model=List[schemas.WorkoutPlanOut])
def get_workout_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.list_workout_plans(db, current_user.id)
 
 
@router.post("/workout-plans", response_model=schemas.WorkoutPlanOut, status_code=201)
def add_workout_plan(
    body: schemas.WorkoutPlanIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.create_workout_plan(db, current_user.id, body)
 