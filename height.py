from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from deps import get_current_user
from models import User
from schemas import HeightIn, HeightOut
router = APIRouter(prefix="/users/me/height", tags=["height"])
@router.put("", response_model=HeightOut)
def set_height(
    data: HeightIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Called by the 'Continue' button on the height screen."""
    current_user.height_cm = data.height_cm
    db.commit()
    db.refresh(current_user)
    return HeightOut(height_cm=current_user.height_cm)
@router.get("", response_model=HeightOut)
def get_height(current_user: User = Depends(get_current_user)):
    """Prefill the picker when the user comes back with 'back'."""
    return HeightOut(height_cm=current_user.height_cm)