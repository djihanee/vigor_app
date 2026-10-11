"""
strength_service.py  (version 4)
Logic for the Strength page. No FastAPI here: only plain functions.
NEW in this version (search for "NEW"):
  - weekly tab: real dates, rest days, "4 of 7 days planned this week"
  - plan detail: tap a plan in the weekly list to see its exercises
Every line has a comment, read them from top to bottom.
"""
from datetime import timedelta                     # timedelta = a length of time, e.g. timedelta(days=2)
from typing import List, Optional                  # typing helpers: List[int] = "list of ints", Optional[str] = "a str or None"

from sqlalchemy import func                        # func lets us call SQL functions such as COUNT()
from sqlalchemy.orm import Session                 # Session = one open conversation with the database

import schemas                                     # our Pydantic classes = the shape of the JSON we send back
from models import (ExerciseCompletion, PlanCompletion, PlanExercise, User,   # the database tables we use
                    Workout, WorkoutPlan)
from profile_service import current_weight         # latest weight of a user (to estimate calories)
from progress_service import current_streak, today, week_start_of   # streak, today's date (UTC), Monday of a week

# ------------------------------------------------------------------ settings
# MET = how intense an activity is. Formula: calories = MET x weight(kg) x hours
MET_BY_CATEGORY = {"strength": 5.0, "cardio": 7.0, "hiit": 8.0, "stretching": 2.5}   # intensity per category
DEFAULT_WEIGHT_KG = 70                             # used if we don't know the user's weight
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]   # index 0 = Monday (same as Python's weekday())


# ------------------------------------------------------------------ errors (the router turns them into HTTP codes)
class ExerciseNotFound(Exception):                 # raised when the exercise doesn't exist or isn't the user's
    pass                                           # "pass" = nothing to add, the class name is enough


class NotScheduledToday(Exception):                # raised when the user ticks an exercise of another weekday
    pass


class PlanNotFound(Exception):                     # NEW: raised when the plan doesn't exist or isn't the user's
    pass


# ------------------------------------------------------------------ label helpers
def _format_duration(seconds: int) -> str:         # turns 300 into "5 min" and 30 into "30 sec"
    if seconds % 60 == 0:                          # % gives the remainder: 300 % 60 = 0 -> exact minutes
        return f"{seconds // 60} min"              # // is whole-number division: 300 // 60 = 5
    return f"{seconds} sec"                        # otherwise keep seconds (30 % 60 = 30, not 0)


def exercise_label(ex: PlanExercise) -> str:      # the small grey text under each exercise name
    amount = f"{ex.reps} reps" if ex.reps else _format_duration(ex.duration_sec)   # reps if we have them, else a time
    if ex.sets == 1 and not ex.reps:               # one single timed block, like the jump rope or a HIIT move
        return amount                              # -> "5 min" or "30 sec" (no "1 sets x ...")
    sets_word = "set" if ex.sets == 1 else "sets"  # grammar: 1 set, 2 sets
    return f"{ex.sets} {sets_word} x {amount}"     # -> "3 sets x 30 sec" or "3 sets x 10 reps"


def estimate_calories(category: str, weight_kg: float, duration_min: int) -> int:
    met = MET_BY_CATEGORY.get(category, 5.0)       # find the intensity, 5.0 if the category is unknown
    return round(met * weight_kg * duration_min / 60)   # minutes / 60 = hours, round() gives a whole number


# ------------------------------------------------------------------ small database helpers
def _plan_exercises(db: Session, plan_id: int) -> List[PlanExercise]:   # the exercises of one plan
    return (
        db.query(PlanExercise)                                  # SELECT * FROM plan_exercises
        .filter(PlanExercise.plan_id == plan_id)                # WHERE plan_id = ...
        .order_by(PlanExercise.position, PlanExercise.id)       # keep the order chosen when the plan was created
        .all()                                                  # run the query and return a list
    )


def _done_ids(db: Session, user_id: int, exercise_ids: List[int]) -> set:   # which exercises are ticked TODAY
    if not exercise_ids:                           # empty plan -> nothing can be ticked
        return set()                               # an empty set
    rows = (
        db.query(ExerciseCompletion.exercise_id)               # we only need the exercise ids
        .filter(ExerciseCompletion.user_id == user_id,         # of this user
                ExerciseCompletion.day == today(),             # ticked today (tomorrow all circles are empty again)
                ExerciseCompletion.exercise_id.in_(exercise_ids))   # among the exercises we are asking about
        .all()
    )
    return {eid for (eid,) in rows}                # each row is a 1-item tuple (id,); we unpack it and build a set


def _is_completed(db: Session, user_id: int, plan_id: int) -> bool:   # was this plan already finished today?
    return (
        db.query(PlanCompletion.id)
        .filter(PlanCompletion.user_id == user_id,
                PlanCompletion.plan_id == plan_id,
                PlanCompletion.day == today())
        .first()                                   # first matching row, or None
        is not None                                # True if a row exists
    )


def _pick_today_plan(db: Session, user_id: int, category: Optional[str]) -> Optional[WorkoutPlan]:
    query = db.query(WorkoutPlan).filter(
        WorkoutPlan.user_id == user_id,                    # only this user's plans
        WorkoutPlan.weekday == today().weekday(),          # scheduled for today's weekday (0 = Monday)
    )
    if category:                                           # a chip is selected
        query = query.filter(WorkoutPlan.category == category)   # keep only plans of that category
    return query.order_by(WorkoutPlan.id).first()          # the oldest one, or None if there is no plan


def _pick_next_plan(db: Session, user_id: int, category: str) -> Optional[WorkoutPlan]:
    plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id, WorkoutPlan.category == category)   # all plans of this category
        .all()
    )
    if not plans:                                          # the user never created a plan of this category
        return None
    today_weekday = today().weekday()                      # 0 = Monday ... 6 = Sunday
    # days until each plan comes again: (plan day - today) % 7. Example: today Thu(3), plan Mon(0) -> (0-3) % 7 = 4
    return min(plans, key=lambda p: ((p.weekday - today_weekday) % 7, p.id))   # smallest number = the soonest plan


def _categories_today(db: Session, user_id: int) -> List[str]:   # which chips have a plan today
    rows = (
        db.query(WorkoutPlan.category)
        .filter(WorkoutPlan.user_id == user_id, WorkoutPlan.weekday == today().weekday())
        .distinct()                                        # each category only once
        .all()
    )
    return sorted(c for (c,) in rows)                      # ["cardio", "strength"] in alphabetical order


# ------------------------------------------------------------------ the AI coach strip at the bottom
def coach_tip(db: Session, user_id: int, has_plan: bool, completed: bool) -> str:
    if not has_plan:                                       # nothing planned
        return "No workout planned today. Enjoy your rest day."
    streak = current_streak(db, user_id)                   # days in a row with at least one workout
    if completed:                                          # the user just finished
        return f"Workout done! You're on a {streak}-day streak. Keep it going tomorrow."
    if streak > 0:                                         # streak alive, workout not done yet
        return f"you're {streak} days into your streak, finish today's workout to keep going"
    return "Finish today's workout to start your streak."  # no streak yet


# ------------------------------------------------------------------ TODAY PLAN tab
def build_today(db: Session, user: User, category: Optional[str] = None) -> schemas.TodayWorkoutOut:
    available = _categories_today(db, user.id)             # chips that have a plan today
    plan = _pick_today_plan(db, user.id, category)         # the plan scheduled for today (None if there isn't one)

    upcoming = False                                       # are we showing a future plan instead of today's?
    if plan is None and category:                          # this chip has nothing today...
        plan = _pick_next_plan(db, user.id, category)      # ...so look for the next plan of this category
        upcoming = plan is not None                        # True only if we really found one

    if plan is None:                                       # still nothing to show
        if category:                                       # the user has no plan of this category at all
            tip = f"No {category} workout planned yet."
        else:                                              # no category chosen and nothing today
            tip = coach_tip(db, user.id, has_plan=False, completed=False)
        return schemas.TodayWorkoutOut(
            plan=None, exercises=[], done_count=0, total_count=0,
            next_exercise_id=None, coach_tip=tip, available_categories=available,
        )

    exercises = _plan_exercises(db, plan.id)               # the exercises of the plan
    weekday_label = DAY_LABELS[plan.weekday]               # "Wed", shown on the card for an upcoming plan

    if upcoming:                                           # a future plan is read-only
        done = set()                                       # nothing is ticked
        completed = False                                  # it can't be finished yet
        status = "upcoming"                                # the app shows "Next: Wed" instead of "Scheduled"
        tip = f"Your next {plan.category} workout is on {weekday_label}."   # replaces the streak message
    else:                                                  # today's plan
        done = _done_ids(db, user.id, [e.id for e in exercises])   # ids of the ticked ones (a set)
        completed = _is_completed(db, user.id, plan.id)    # finished today?
        if completed:                                      # the label on the card
            status = "completed"
        elif done:                                         # at least one exercise ticked
            status = "in_progress"
        else:
            status = "scheduled"                           # the word "Scheduled" in your design
        tip = coach_tip(db, user.id, has_plan=True, completed=completed)

    next_exercise = next((e for e in exercises if e.id not in done), None)   # first exercise not ticked yet, or None
    if upcoming:                                           # nothing to "continue" on a future plan
        next_exercise = None

    return schemas.TodayWorkoutOut(
        plan=schemas.TodayPlanOut(                         # the card: name, minutes, count, status
            id=plan.id, name=plan.name, category=plan.category,
            duration_min=plan.duration_min, exercises_count=len(exercises), status=status,
            weekday=plan.weekday, weekday_label=weekday_label,   # which day this plan belongs to
            is_today=not upcoming,                         # False -> the app disables the circles and the button
        ),
        exercises=[                                        # one item per exercise row on the screen
            schemas.ExerciseOut(
                id=e.id, name=e.name, sets=e.sets, reps=e.reps, duration_sec=e.duration_sec,
                label=exercise_label(e),                   # "3 sets x 30 sec"
                done=e.id in done,                         # True -> the circle is filled
            )
            for e in exercises                             # list comprehension: repeat for every exercise
        ],
        done_count=len(done),                              # the "2 / 6 done" -> 2
        total_count=len(exercises),                        # -> 6
        next_exercise_id=next_exercise.id if next_exercise else None,   # where "continue workouts" resumes
        coach_tip=tip,
        available_categories=available,                    # lets the app mark chips that have a plan today
    )


# ------------------------------------------------------------------ ticking an exercise
def _log_workout_if_finished(db: Session, user: User, plan: WorkoutPlan) -> None:
    exercises = _plan_exercises(db, plan.id)               # all the exercises of the plan
    done = _done_ids(db, user.id, [e.id for e in exercises])   # the ticked ones
    if not exercises or len(done) < len(exercises) or _is_completed(db, user.id, plan.id):
        return                                             # not finished yet, or already logged: do nothing

    weight = current_weight(db, user) or DEFAULT_WEIGHT_KG # user's weight, or 70 if unknown
    workout = Workout(                                     # a normal workout row, like POST /progress/workouts
        user_id=user.id,
        calories_burned=estimate_calories(plan.category, weight, plan.duration_min),
        duration_min=plan.duration_min,
    )
    db.add(workout)                                        # stage it (not saved yet)
    db.flush()                                             # send it to the DB now so workout.id exists
    db.add(PlanCompletion(user_id=user.id, plan_id=plan.id, day=today(), workout_id=workout.id))   # remember "finished"


def _undo_workout_if_unfinished(db: Session, user: User, plan: WorkoutPlan) -> None:
    row = (
        db.query(PlanCompletion)                           # was this plan marked as finished today?
        .filter(PlanCompletion.user_id == user.id,
                PlanCompletion.plan_id == plan.id,
                PlanCompletion.day == today())
        .first()
    )
    if row is None:                                        # it wasn't finished: nothing to undo
        return
    db.query(Workout).filter(Workout.id == row.workout_id).delete()   # delete the workout we created
    db.delete(row)                                         # and the "finished" marker


def set_exercise_done(db: Session, user: User, exercise_id: int, done: bool) -> schemas.TodayWorkoutOut:
    exercise = (
        db.query(PlanExercise)
        .join(WorkoutPlan, PlanExercise.plan_id == WorkoutPlan.id)    # link each exercise to its plan
        .filter(PlanExercise.id == exercise_id, WorkoutPlan.user_id == user.id)   # must be THIS user's plan
        .first()
    )
    if exercise is None:                                   # unknown id, or somebody else's exercise
        raise ExerciseNotFound()

    plan = db.get(WorkoutPlan, exercise.plan_id)           # load the plan by its primary key
    if plan.weekday != today().weekday():                  # you can't tick Friday's exercise on Thursday
        raise NotScheduledToday()                          # this also protects the "upcoming" plans

    existing = (
        db.query(ExerciseCompletion)                       # is it already ticked today?
        .filter(ExerciseCompletion.user_id == user.id,
                ExerciseCompletion.exercise_id == exercise_id,
                ExerciseCompletion.day == today())
        .first()
    )
    if done and existing is None:                          # user ticks it -> add a row
        db.add(ExerciseCompletion(user_id=user.id, exercise_id=exercise_id, day=today()))
    elif not done and existing is not None:               # user un-ticks it -> remove the row
        db.delete(existing)
    db.flush()                                             # apply now so the counts below see the change

    if done:
        _log_workout_if_finished(db, user, plan)           # maybe this was the last one
    else:
        _undo_workout_if_unfinished(db, user, plan)        # maybe the plan was finished before

    db.commit()                                            # save everything in ONE transaction
    return build_today(db, user, plan.category)            # same category, so the screen shows the plan just edited


# ------------------------------------------------------------------ WEEKLY PLAN tab
def _plan_item(plan: WorkoutPlan, counts: dict) -> schemas.WeeklyPlanItem:   # NEW: one small card, e.g. "Cardio Blast"
    return schemas.WeeklyPlanItem(
        id=plan.id, name=plan.name, category=plan.category, duration_min=plan.duration_min,
        exercises_count=counts.get(plan.id, plan.exercises_count),   # real count, or the stored one if none found
    )


def weekly_plans(db: Session, user_id: int, category: Optional[str] = None) -> schemas.WeeklyOut:   # NEW shape
    start = week_start_of(today())                         # NEW: the Monday of this week (a date)
    all_plans = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == user_id)            # ALL the user's plans, whatever the category
        .order_by(WorkoutPlan.weekday, WorkoutPlan.id)     # Monday first
        .all()
    )

    counts = dict(                                         # {plan_id: number of exercises}
        db.query(PlanExercise.plan_id, func.count(PlanExercise.id))        # COUNT per plan
        .group_by(PlanExercise.plan_id)                    # one result row per plan
        .all()
    )

    by_day = {i: [] for i in range(7)}                     # {0: [], 1: [], ... 6: []}: an empty list per weekday
    for p in all_plans:                                    # put every plan in its weekday's list
        by_day[p.weekday].append(p)

    planned_days = sum(1 for plans in by_day.values() if plans)   # NEW: days that have at least one plan ("4")

    days = []                                              # NEW: the 7 cards of the screen
    for i in range(7):                                     # i = 0 (Monday) ... 6 (Sunday)
        shown = [p for p in by_day[i] if not category or p.category == category]   # apply the chip filter, if any
        day_date = start + timedelta(days=i)               # NEW: the real date of that day this week
        days.append(
            schemas.WeeklyDayOut(
                weekday=i, label=DAY_LABELS[i],            # 2 = "Wed"
                date=day_date, day_number=day_date.day,    # NEW: the big number on the card (3, 4, 5...)
                is_today=(i == today().weekday()),         # the highlighted border on the card
                is_rest_day=len(by_day[i]) == 0,           # NEW: True -> the moon icon (based on ALL plans, not the filter)
                plans=[_plan_item(p, counts) for p in shown],
            )
        )

    return schemas.WeeklyOut(
        week_start=start,
        planned_days=planned_days,                         # 4
        total_days=7,
        summary=f"{planned_days} of 7 days planned this week",   # the grey sentence under the tabs
        days=days,
    )


# ------------------------------------------------------------------ PLAN DETAIL (tap a plan in the weekly list)
def get_plan_detail(db: Session, user_id: int, plan_id: int) -> schemas.PlanDetailOut:   # NEW
    plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id)   # must be THIS user's plan (security)
        .first()
    )
    if plan is None:                                       # unknown id, or somebody else's plan
        raise PlanNotFound()

    exercises = _plan_exercises(db, plan.id)               # the plan's exercises, in order
    return schemas.PlanDetailOut(
        id=plan.id, name=plan.name, category=plan.category, duration_min=plan.duration_min,
        weekday=plan.weekday, weekday_label=DAY_LABELS[plan.weekday],
        exercises_count=len(exercises),
        exercises=[
            schemas.PlanExerciseOut(                       # same as ExerciseOut but without "done" (it's just a preview)
                id=e.id, name=e.name, sets=e.sets, reps=e.reps, duration_sec=e.duration_sec,
                label=exercise_label(e),
            )
            for e in exercises
        ],
    )


# ------------------------------------------------------------------ creating a plan (so the page has data)
def create_plan(db: Session, user_id: int, data: schemas.PlanCreate) -> schemas.WeeklyPlanItem:
    plan = WorkoutPlan(                                    # the plan row
        user_id=user_id, name=data.name, category=data.category,
        duration_min=data.duration_min, weekday=data.weekday,
        exercises_count=len(data.exercises),               # Home page still reads this column
    )
    db.add(plan)                                           # stage it
    db.flush()                                             # send it now so plan.id exists

    for position, ex in enumerate(data.exercises):         # enumerate gives 0, 1, 2... = the screen order
        db.add(PlanExercise(plan_id=plan.id, position=position, **ex.model_dump()))   # ** spreads name/sets/reps/duration_sec

    db.commit()                                            # save the plan and all its exercises together
    db.refresh(plan)                                       # reload the plan from the database
    return schemas.WeeklyPlanItem(
        id=plan.id, name=plan.name, category=plan.category,
        duration_min=plan.duration_min, exercises_count=plan.exercises_count,
    )