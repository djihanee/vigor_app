from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import coach_service as service
import schemas
from deps import get_current_user, get_db   # <- adapt to your project
from models import User
router = APIRouter(prefix="/coach", tags=["AI Coach"])
@router.get("/messages", response_model=List[schemas.ChatMessageOut])
def get_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat history (oldest first)."""
    return service.list_messages(db, current_user.id)
@router.post("/start", response_model=List[schemas.ChatMessageOut])
def start_chat(
    local_hour: Optional[int] = Query(default=None, ge=0, le=23),  # phone's hour -> "Good morning"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Call when the screen opens. Adds the coach greeting if the chat is empty."""
    return service.start_conversation(db, current_user, local_hour)
@router.post("/messages", response_model=schemas.ChatReplyOut, status_code=201)
def send_message(
    body: schemas.ChatIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The send button: saves the user's message, asks Claude, returns both messages."""
    try:
        user_msg, coach_msg = service.ask_coach(db, current_user, body.content.strip())
    except service.CoachLimitReached:
        raise HTTPException(status_code=429, detail="Daily message limit reached. Come back tomorrow!")
    except service.CoachUnavailable:
        raise HTTPException(status_code=503, detail="The coach is unavailable right now. Try again in a moment.")
    return {"user_message": user_msg, "reply": coach_msg}
@router.delete("/messages", status_code=204)
def clear_chat(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service.clear_history(db, current_user.id)