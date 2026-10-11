"""
strength.py  (version 3)
Router for the Strength page. Thin on purpose: receive request -> call the service -> return the result.
NEW: /weekly returns an object (with the "4 of 7" summary) and /plans/{id} shows a plan's exercises.
Every line has a comment.
"""
from typing import List, Optional                    # typing helpers

from fastapi import APIRouter, Depends, HTTPException, Query   # APIRouter groups routes; Depends injects things; Query reads ?params
from sqlalchemy.orm import Session                   # type of the database session

import schemas                                       # response / request shapes
import Strength_service as service                   # all the logic lives here
from deps import get_current_user, get_db            # who is calling + the database connection (adapt to your project)
from models import User                              # type of the logged-in user

router = APIRouter(prefix="/strength", tags=["Strength"])   # every route starts with /strength; "tags" groups them in /docs


@router.get("/today", response_model=schemas.TodayWorkoutOut)   # GET /strength/today ; the answer must match TodayWorkoutOut
def get_today(
    category: Optional[schemas.Category] = Query(default=None),   # ?category=cardio (the selected chip). Optional.
    db: Session = Depends(get_db),                                 # FastAPI opens a database session for us
    current_user: User = Depends(get_current_user),                # FastAPI finds who is calling from the token
):
    """'Today plan' tab: the card, the exercises, '2 / 6 done' and the coach strip."""
    return service.build_today(db, current_user, category)        # the service does the work


@router.get("/weekly", response_model=schemas.WeeklyOut)           # NEW: the answer is now ONE object, not a bare list
def get_weekly(
    category: Optional[schemas.Category] = Query(default=None),   # optional filter, same values as the chips
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """'Weekly plan' tab: '4 of 7 days planned' + the 7 day cards."""
    return service.weekly_plans(db, current_user.id, category)


@router.get("/plans/{plan_id}", response_model=schemas.PlanDetailOut)   # NEW: GET /strength/plans/5
def get_plan(
    plan_id: int,                                    # taken from the URL
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tapping a day card: the plan's exercises (read-only preview)."""
    try:
        return service.get_plan_detail(db, current_user.id, plan_id)
    except service.PlanNotFound:                     # service said: not found / not yours
        raise HTTPException(status_code=404, detail="Plan not found")


@router.patch("/exercises/{exercise_id}", response_model=schemas.TodayWorkoutOut)   # PATCH = change part of something
def tick_exercise(
    exercise_id: int,                                # taken from the URL: /strength/exercises/12 -> 12
    body: schemas.ExerciseDoneIn,                    # JSON body {"done": true}, validated by Pydantic
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tick or un-tick the circle next to an exercise. Returns the refreshed screen."""
    try:
        return service.set_exercise_done(db, current_user, exercise_id, body.done)
    except service.ExerciseNotFound:                 # service said: not found / not yours
        raise HTTPException(status_code=404, detail="Exercise not found")
    except service.NotScheduledToday:                # service said: wrong weekday
        raise HTTPException(status_code=400, detail="This exercise is not scheduled for today")


@router.post("/plans", response_model=schemas.WeeklyPlanItem, status_code=201)   # 201 = "created"
def create_plan(
    body: schemas.PlanCreate,                        # the plan + its exercises, validated
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a plan with all its exercises in one request."""
    return service.create_plan(db, current_user.id, body)