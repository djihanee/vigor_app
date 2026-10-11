from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import models, schemas
from database import get_db
from deps import get_current_user
router = APIRouter(prefix="/users/me", tags=["activity"])
@router.get("/activity-level", response_model=schemas.ActivityOut)
def get_activity_level(current_user: models.User = Depends(get_current_user)):
    return schemas.ActivityOut(activity_level=current_user.activity_level)
@router.put("/activity-level", response_model=schemas.ActivityOut)
def set_activity_level(
    data: schemas.ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    current_user.activity_level = data.activity_level.value
    db.commit()
    db.refresh(current_user)
    return schemas.ActivityOut(activity_level=current_user.activity_level)