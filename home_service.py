from datetime import datetime, time, timedelta, timezone
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
import schemas
from models import (FoodLog, SleepLog, StepLog, User, WaterLog, WorkoutPlan,
                    Workout)
from profile_service import current_weight   # latest weight (log, else signup weight)
from progress_service import today           # today's date (UTC), same as the other pages
# ------------------------------------------------------------------ settings
DAILY_BURN_GOAL_KCAL = 600     # the goal behind the "68%" ring (make it per-user later)
DEFAULT_CALORIE_TARGET = 2000  # used when the user profile is incomplete
 
ACTIVITY_FACTORS = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
GOAL_ADJUSTMENT = {"lose_weight": -500, "build_muscle": 300, "maintain": 0}
# ------------------------------------------------------------------ helpers
def day_bounds():
    """Datetime range that covers 'today' (00:00 -> tomorrow 00:00, UTC)."""
    d = today()
    start = datetime.combine(d, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)
# ------------------------------------------------------------------ today's progress (ring)
def calories_burned_today(db: Session, user_id: int) -> int:
    """The '420 Kcal burned' number: sum of today's workouts."""
    start, end = day_bounds()
    total = (
        db.query(func.coalesce(func.sum(Workout.calories_burned), 0))
        .filter(Workout.user_id == user_id,
                Workout.performed_at >= start,
                Workout.performed_at < end)
        .scalar()
    )
    return int(total)
def today_progress(db: Session, user_id: int) -> schemas.TodayProgressOut:
    burned = calories_burned_today(db, user_id)
    percent = min(100, round(burned / DAILY_BURN_GOAL_KCAL * 100))   # the '68%'
    return schemas.TodayProgressOut(
        kcal_burned=burned, goal_kcal=DAILY_BURN_GOAL_KCAL, percent=percent
    )
# ------------------------------------------------------------------ calories left (card 1)
def daily_calorie_target(user: User, weight_kg: Optional[float]) -> int:
    """
    How many calories the user should EAT per day.
    Mifflin-St Jeor formula (BMR) x activity factor, then +/- depending on the goal.
    """
    if user.age is None or user.height_cm is None or weight_kg is None:
        return DEFAULT_CALORIE_TARGET
    is_female = (user.gender or "").lower().startswith("f")
    bmr = 10 * weight_kg + 6.25 * user.height_cm - 5 * user.age + (-161 if is_female else 5)
    factor = ACTIVITY_FACTORS.get(user.activity_level, 1.2)
    target = bmr * factor + GOAL_ADJUSTMENT.get(user.goal, 0)
    return max(1200, round(target))   # never go below a safe minimum
def calories_eaten_today(db: Session, user_id: int) -> int:
    start, end = day_bounds()
    total = (
        db.query(func.coalesce(func.sum(FoodLog.calories), 0))
        .filter(FoodLog.user_id == user_id,
                FoodLog.logged_at >= start,
                FoodLog.logged_at < end)
        .scalar()
    )
    return int(total)
def calories_left(db: Session, user: User) -> int:
    """The '1,850 calories left' number = daily target - food eaten today."""
    target = daily_calorie_target(user, current_weight(db, user))
    return max(0, target - calories_eaten_today(db, user.id))
# ------------------------------------------------------------------ water / steps / sleep
def water_today_ml(db: Session, user_id: int) -> int:
    """The '1.4 L' card (returned in ml: 1400)."""
    start, end = day_bounds()
    total = (
        db.query(func.coalesce(func.sum(WaterLog.amount_ml), 0))
        .filter(WaterLog.user_id == user_id,
                WaterLog.logged_at >= start,
                WaterLog.logged_at < end)
        .scalar()
    )
    return int(total)
def steps_today(db: Session, user_id: int) -> int:
    """The '6,240 steps' card."""
    row = db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.day == today()).first()
    return row.steps if row else 0
def sleep_today_minutes(db: Session, user_id: int) -> int:
    """The '7h 20m' card (returned in minutes: 440)."""
    row = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.day == today()).first()
    return row.minutes if row else 0
# ------------------------------------------------------------------ today's workout
def todays_workout(db: Session, user_id: int) -> Optional[WorkoutPlan]:
    """The 'Upper body strength' card: the plan scheduled for today's weekday."""
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id, WorkoutPlan.weekday == today().weekday())
        .order_by(WorkoutPlan.id)
        .first()
    )
def list_workout_plans(db: Session, user_id: int) -> List[WorkoutPlan]:
    """The 'see all' link."""
    return (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)
        .order_by(WorkoutPlan.weekday, WorkoutPlan.id)
        .all()
    )
# ------------------------------------------------------------------ whole page
def build_home(db: Session, user: User) -> schemas.HomeOut:
    plan = todays_workout(db, user.id)
    return schemas.HomeOut(
        username=user.username,
        today_progress=today_progress(db, user.id),
        calories_left=calories_left(db, user),
        water_ml=water_today_ml(db, user.id),
        steps=steps_today(db, user.id),
        sleep_minutes=sleep_today_minutes(db, user.id),
        todays_workout=schemas.WorkoutPlanOut.model_validate(plan) if plan else None,
    )
# ------------------------------------------------------------------ logging (so the cards have data)
def log_water(db: Session, user_id: int, amount_ml: int) -> int:
    db.add(WaterLog(user_id=user_id, amount_ml=amount_ml))
    db.commit()
    return water_today_ml(db, user_id)
def set_steps(db: Session, user_id: int, steps: int) -> int:
    """Phones send the running total for the day, so we replace (upsert) instead of adding."""
    row = db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.day == today()).first()
    if row:
        row.steps = steps
    else:
        db.add(StepLog(user_id=user_id, day=today(), steps=steps))
    db.commit()
    return steps
def set_sleep(db: Session, user_id: int, minutes: int) -> int:
    row = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.day == today()).first()
    if row:
        row.minutes = minutes
    else:
        db.add(SleepLog(user_id=user_id, day=today(), minutes=minutes))
    db.commit()
    return minutes
def log_food(db: Session, user_id: int, data: schemas.FoodIn) -> int:
    db.add(FoodLog(user_id=user_id, **data.model_dump()))
    db.commit()
    return calories_eaten_today(db, user_id)
def create_workout_plan(db: Session, user_id: int, data: schemas.WorkoutPlanIn) -> WorkoutPlan:
    plan = WorkoutPlan(user_id=user_id, **data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
 