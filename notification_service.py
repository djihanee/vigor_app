from typing import List
from sqlalchemy.orm import Session
import schemas
from models import DeviceToken, NotificationSettings
# The individual switches on the screen (the master switch `push_enabled` is separate).
SETTING_FIELDS = (
    "daily_workout_reminder",
    "rest_day_checkin",
    "missed_workout_alert",
    "streak_reminders",
    "weekly_summary",
    "ai_coach_messages",
    "app_updates",
)
# ------------------------------------------------------------------ read / update the switches
def get_or_create_settings(db: Session, user_id: int) -> NotificationSettings:
    """
    Returns the user's settings. First time: creates a row with the default values
    (the ones you see in the design), so the screen always has something to show.
    """
    settings = db.query(NotificationSettings).filter(NotificationSettings.user_id == user_id).first()
    if settings is None:
        settings = NotificationSettings(user_id=user_id)   # column defaults are applied
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
def update_settings(db: Session, user_id: int, data: schemas.NotificationSettingsUpdate) -> NotificationSettings:
    """
    Partial update: only the switches the app sent are changed.
    `None` values are ignored, because none of these columns can be empty.
    """
    settings = get_or_create_settings(db, user_id)
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    for field, value in changes.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings
# ------------------------------------------------------------------ used later by the code that SENDS notifications
def is_enabled(settings: NotificationSettings, name: str) -> bool:
    """
    True only if the master switch is on AND the individual switch is on.
    The master switch overrides everything, but it doesn't erase the other values,
    so turning it back on restores the user's previous choices.
    """
    if name not in SETTING_FIELDS:
        raise ValueError(f"Unknown notification setting: {name}")
    return bool(settings.push_enabled and getattr(settings, name))
def user_ids_with_setting(db: Session, name: str) -> List[int]:
    """
    Every user who wants a given kind of notification, e.g. 'weekly_summary'.
    A scheduled job will call this to know who to send to.
    """
    if name not in SETTING_FIELDS:
        raise ValueError(f"Unknown notification setting: {name}")
    rows = ( 
        db.query(NotificationSettings.user_id)
        .filter(NotificationSettings.push_enabled.is_(True),
                getattr(NotificationSettings, name).is_(True))
        .all()
    )
    return [user_id for (user_id,) in rows]
# ------------------------------------------------------------------ device tokens (needed for push to reach the phone)
def register_device_token(db: Session, user_id: int, data: schemas.DeviceTokenIn) -> None:
    """
    Saves the phone's push token. If the token already exists (same phone, another account),
    it is moved to the current user, so one phone never receives two users' notifications.
    """
    row = db.query(DeviceToken).filter(DeviceToken.token == data.token).first()
    if row:
        row.user_id = user_id
        row.platform = data.platform
    else:
        db.add(DeviceToken(user_id=user_id, token=data.token, platform=data.platform))
    db.commit()
def remove_device_token(db: Session, user_id: int, token: str) -> None:
    """Call on log out, so the phone stops receiving this user's notifications."""
    db.query(DeviceToken).filter(DeviceToken.user_id == user_id, DeviceToken.token == token).delete()
    db.commit()
def get_user_tokens(db: Session, user_id: int) -> List[str]:
    return [t for (t,) in db.query(DeviceToken.token).filter(DeviceToken.user_id == user_id).all()]
 