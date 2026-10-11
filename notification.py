"""
notifications.py
Router for the Notifications settings page. Thin on purpose: receive request -> call service -> return.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import notification_service as service
import schemas
from deps import get_current_user, get_db   # <- adapt to your project
from models import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/settings", response_model=schemas.NotificationSettingsOut)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feeds the whole screen (all the switches)."""
    return service.get_or_create_settings(db, current_user.id)


@router.patch("/settings", response_model=schemas.NotificationSettingsOut)
def update_settings(
    body: schemas.NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Called each time the user flips a switch. Send only the switch that changed."""
    return service.update_settings(db, current_user.id, body)


@router.post("/device-token", status_code=201)
def register_token(
    body: schemas.DeviceTokenIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The app sends the phone's push token after the user allows notifications."""
    service.register_device_token(db, current_user.id, body)
    return {"ok": True}


@router.delete("/device-token", status_code=204)
def remove_token(
    token: str = Query(min_length=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Call on log out."""
    service.remove_device_token(db, current_user.id, token)