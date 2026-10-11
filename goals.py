from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from deps import  get_current_user
router = APIRouter(prefix="/users/me", tags=["goals"])
@router.get("/goal", response_model=schemas.GoalOut)
def get_goal(current_user: models.User = Depends(get_current_user)):
    return schemas.GoalOut(goal=current_user.goal)
@router.put("/goal", response_model=schemas.GoalOut)
def set_goal(
    data: schemas.GoalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    current_user.goal = data.goal.value
    db.commit()
    db.refresh(current_user)
    return schemas.GoalOut(goal=current_user.goal)