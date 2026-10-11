from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from deps import get_current_user
from models import User
from schemas import GenderUpdate, userout
from schemas import AgeUpdate, AgeResponse
router = APIRouter(prefix="/users", tags=["users"])
@router.put("/me/gender", response_model=userout)
def set_gender(data: GenderUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.gender = data.gender
    db.commit()
    db.refresh(user)
    return user
@router.put("/me/age", response_model=AgeResponse)
def update_age(
    data: AgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.age = data.age
    db.commit()
    db.refresh(current_user)
    return current_user
@router.get("/me/age", response_model=AgeResponse)
def get_age(current_user: User = Depends(get_current_user)):
    return current_user
