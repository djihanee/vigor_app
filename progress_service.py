from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional, Set
from sqlalchemy.orm import Session
import schemas
from models import WeightLog, Workout
LABELS = ["M", "T", "W", "T", "F", "S", "S"]  # Monday -> Sunday
# ------------------------------------------------------------------ helpers
def today() -> date:
    return datetime.now(timezone.utc).date()
def week_start_of(d: date, offset_weeks: int = 0) -> date:
    """Monday of the week containing d. offset_weeks=-1 -> last week."""
    return d - timedelta(days=d.weekday()) + timedelta(weeks=offset_weeks)
def _day_bounds(start: date, end: date):
    """Datetime range covering start 00:00 up to the end of day `end`."""
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start_dt, end_dt
# ------------------------------------------------------------------ calories (bar chart)
def calories_for_week(db: Session, user_id: int, week_offset: int = 0) -> schemas.CaloriesOut:
    start = week_start_of(today(), week_offset)
    end = start + timedelta(days=6)
    start_dt, end_dt = _day_bounds(start, end)
    workouts = (
        db.query(Workout)
        .filter(
            Workout.user_id == user_id,
            Workout.performed_at >= start_dt,
            Workout.performed_at < end_dt,
        )
        .all()
    )
    # sum calories per date
    per_day = {}
    for w in workouts:
        d = w.performed_at.date()
        per_day[d] = per_day.get(d, 0) + w.calories_burned
 
    days: List[schemas.DayCalories] = []
    for i in range(7):
        d = start + timedelta(days=i)
        days.append(
            schemas.DayCalories(
                label=LABELS[i],
                date=d,
                calories=per_day.get(d, 0),   # no workout -> 0, so we always return 7 days
                is_today=(d == today()),
            )
        )
    return schemas.CaloriesOut(week_start=start, days=days)
# ------------------------------------------------------------------ weight (line chart + -2.4kg)
def _weight_logs(db: Session, user_id: int, days: int) -> List[WeightLog]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return (
        db.query(WeightLog)
        .filter(WeightLog.user_id == user_id, WeightLog.logged_at >= since)
        .order_by(WeightLog.logged_at)
        .all()
    )
 
 
def weight_trend(db: Session, user_id: int, days: int = 30) -> schemas.WeightTrendOut:
    logs = _weight_logs(db, user_id, days)
    return schemas.WeightTrendOut(
        points=[
            schemas.WeightPoint(date=l.logged_at.date(), weight_kg=l.weight_kg) for l in logs
        ],
        start_label=f"{days}d ago",
        end_label="Today",
    )
# ------------------------------------------------------------------ streak
def _workout_dates(db: Session, user_id: int) -> Set[date]:
    rows = db.query(Workout.performed_at).filter(Workout.user_id == user_id).all()
    return {ts.date() for (ts,) in rows}
def current_streak(db: Session, user_id: int) -> int:
    """
    Number of consecutive days with at least one workout.
    If today has no workout yet, the streak is still alive: we count from yesterday.
    """
    days = _workout_dates(db, user_id)
    cursor = today()
    if cursor not in days:
        cursor -= timedelta(days=1)
 
    streak = 0
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
# ------------------------------------------------------------------ summary (2 cards)
def summary(db: Session, user_id: int) -> schemas.SummaryOut:
    logs = _weight_logs(db, user_id, 30)
    change: Optional[float] = None
    if len(logs) >= 2:
        change = round(logs[-1].weight_kg - logs[0].weight_kg, 1)
 
    return schemas.SummaryOut(
        weight_change_kg=change,
        current_streak_days=current_streak(db, user_id),
    )
# ------------------------------------------------------------------ weekly consistency (7 circles)
def consistency(db: Session, user_id: int, week_offset: int = 0) -> schemas.ConsistencyOut:
    start = week_start_of(today(), week_offset)
    done_dates = _workout_dates(db, user_id)
    days = []
    for i in range(7):
        d = start + timedelta(days=i)
        days.append(schemas.ConsistencyDay(label=LABELS[i], date=d, done=d in done_dates))
    return schemas.ConsistencyOut(days=days)
# ------------------------------------------------------------------ everything
def full_progress(db: Session, user_id: int) -> schemas.ProgressOut:
    return schemas.ProgressOut(
        calories=calories_for_week(db, user_id),
        summary=summary(db, user_id),
        weight_trend=weight_trend(db, user_id, 30),
        consistency=consistency(db, user_id),
    )
 
