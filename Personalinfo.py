"""
personal_info.py
Router for the "Edit personal info" page. Thin on purpose: receive request -> call service -> return.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

import Personalinfo_service as service
import schemas
from deps import get_current_user, get_db   # <- adapt to your project
from models import User

router = APIRouter(prefix="/profile", tags=["Edit personal info"])


@router.get("/personal-info", response_model=schemas.PersonalInfoOut)
def get_personal_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fills the form (name, email, gender, age, height, weight, photo)."""
    return service.get_personal_info(db, current_user)


@router.patch("/personal-info", response_model=schemas.PersonalInfoOut)
def save_personal_info(
    body: schemas.PersonalInfoIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """'Save changes' button."""
    try:
        return service.save_personal_info(db, current_user, body)
    except service.EmailTaken:
        raise HTTPException(status_code=409, detail="This email is already used by another account.")
    except service.EmailManagedByProvider:
        raise HTTPException(status_code=400, detail="Your email is managed by your sign-in provider and can't be changed here.")


@router.post("/avatar")
def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Camera button. Send the photo as multipart/form-data in a field called 'file'."""
    data = file.file.read(service.MAX_AVATAR_BYTES + 1)   # read one byte more than the limit to detect big files
    try:
        url = service.save_avatar(db, current_user.id, data)
    except service.ImageTooLarge:
        raise HTTPException(status_code=413, detail="Image too large (max 2 MB).")
    except service.InvalidImage:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG or WEBP images are allowed.")
    return {"avatar_url": url}


@router.delete("/avatar", status_code=204)
def remove_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.delete_avatar(db, current_user.id)