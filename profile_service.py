from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
import schemas
from models import Reminder, User, WeightLog, Workout
from progress_service import current_streak  
# ------------------------------------------------------------------ stats (3 cards)
def total_workouts(db: Session, user_id: int) -> int:
    """The '42 workout' card: how many workouts the user logged in total."""
    return db.query(func.count(Workout.id)).filter(Workout.user_id == user_id).scalar() or 0
 
 
def current_weight(db: Session, user: User) -> Optional[float]:
    """The '68kg' card: latest weight log. Falls back to the weight from signup."""
    last = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.desc())
        .first()
    )
    return last.weight_kg if last else user.weight_kg
# ------------------------------------------------------------------ goal progress bar
def goal_progress(db: Session, user: User) -> schemas.GoalProgressOut:
    """
    The 'build muscle 58%' bar.
    percent = how far the user went from the START weight towards the TARGET weight.
    The same formula works for gaining and losing weight (the signs cancel out).
    """
    first = (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user.id)
        .order_by(WeightLog.logged_at.asc())
        .first()
    )
    start = first.weight_kg if first else user.weight_kg
    current = current_weight(db, user)
    target = user.target_weight_kg
 
    # not enough data to compute -> frontend can show an empty bar
    if user.goal is None or start is None or current is None or target is None:
        return schemas.GoalProgressOut(goal=user.goal, percent=None)
 
    if target == start:
        percent = 100 if current == target else 0
    else:
        percent = (current - start) / (target - start) * 100
 
    percent = max(0, min(100, round(percent)))  # keep it between 0 and 100
    return schemas.GoalProgressOut(goal=user.goal, percent=percent)
 
 
# ------------------------------------------------------------------ whole page
def build_profile(db: Session, user: User) -> schemas.ProfileOut:
    """Everything the Profile screen needs in one object."""
    return schemas.ProfileOut(
        username=user.username,
        initial=(user.username or user.email)[0].upper(),   # the 'D' in the avatar
        member_since=user.created_at.date() if user.created_at else None,
        stats=schemas.ProfileStats(
            workouts=total_workouts(db, user.id),
            day_streak=current_streak(db, user.id),
            weight_kg=current_weight(db, user),
        ),
        goal_progress=goal_progress(db, user),
        gender=user.gender,
        age=user.age,
        height_cm=user.height_cm,
        goal=user.goal,
        activity_level=user.activity_level,
        target_weight_kg=user.target_weight_kg,
    )
# ------------------------------------------------------------------ "edit personal info"
def update_personal_info(db: Session, user: User, data: schemas.PersonalInfoUpdate) -> User:
    """Update only the fields the client actually sent (exclude_unset)."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user

def update_goals(db: Session, user: User, data: schemas.GoalsUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
 
 
# ------------------------------------------------------------------ "reminders"
def list_reminders(db: Session, user_id: int) -> List[Reminder]:
    return (
        db.query(Reminder)
        .filter(Reminder.user_id == user_id)
        .order_by(Reminder.time_of_day)
        .all()
    )
 
 
def create_reminder(db: Session, user_id: int, data: schemas.ReminderIn) -> Reminder:
    reminder = Reminder(user_id=user_id, **data.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder
 
 
def get_user_reminder(db: Session, user_id: int, reminder_id: int) -> Optional[Reminder]:
    """Only returns the reminder if it belongs to this user (security check)."""
    return (
        db.query(Reminder)
        .filter(Reminder.id == reminder_id, Reminder.user_id == user_id)
        .first()
    )
 
 
def set_reminder_enabled(db: Session, reminder: Reminder, enabled: bool) -> Reminder:
    reminder.enabled = enabled
    db.commit()
    db.refresh(reminder)
    return reminder
 
 
def delete_reminder(db: Session, reminder: Reminder) -> None:
    db.delete(reminder)
    db.commit()
 