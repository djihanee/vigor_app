import os
from typing import List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
import schemas
from home_service import build_home, day_bounds
from models import ChatMessage, User
from progress_service import summary
try:  # load .env if python-dotenv is installed (your project probably already does it)
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from anthropic import Anthropic, APIError
# ------------------------------------------------------------------ settings
COACH_MODEL = os.getenv("COACH_MODEL", "claude-sonnet-5-5")
MAX_REPLY_TOKENS = 400            # keeps answers short (and cheap)
MAX_HISTORY_MESSAGES = 20         # how many old messages the coach "remembers"
MAX_USER_MESSAGES_PER_DAY = 30    # protects your API bill
SYSTEM_PROMPT = """You are "AI Coach", the friendly fitness coach inside the Vega app.
Rules:
- Keep answers short: 1 to 3 sentences, simple words, at most one emoji.
- Use the user's data below to give specific, practical tips. Never invent numbers that are not in the data.
- Calorie burn numbers for activities are estimates: say "about".
- You are not a doctor. For pain, injury, medical conditions, eating disorders or anything risky, \
tell the user to talk to a professional.
- Never encourage extreme dieting or training through pain.
- Reply in the same language the user writes in.
- Only talk about fitness, nutrition, sleep, hydration and motivation. Politely steer back if asked about something else."""

# ------------------------------------------------------------------ errors (the router turns them into HTTP codes)
class CoachLimitReached(Exception):
    pass
class CoachUnavailable(Exception):
    pass
# ------------------------------------------------------------------ Claude client
def get_client() -> Anthropic:
    """Creates the Anthropic client. The key is read from the environment, never hard-coded."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is missing in .env")
    return Anthropic(api_key=api_key)
# ------------------------------------------------------------------ context for the coach
def build_user_context(db: Session, user: User) -> str:
    """Today's real numbers, written as plain text so the coach can use them."""
    home = build_home(db, user)
    stats = summary(db, user.id)
    plan = home.todays_workout
    lines = [
        f"Name: {user.username or 'the user'}",
        f"Goal: {user.goal or 'not set'}; activity level: {user.activity_level or 'not set'}",
        f"Today: burned {home.today_progress.kcal_burned} of {home.today_progress.goal_kcal} kcal "
        f"({home.today_progress.percent}% of the daily goal)",
        f"Calories left to eat today: {home.calories_left}",
        f"Steps today: {home.steps}",
        f"Water today: {home.water_ml} ml",
        f"Sleep last night: {home.sleep_minutes // 60}h {home.sleep_minutes % 60}min",
        f"Today's planned workout: {plan.name + ' (' + str(plan.duration_min) + ' min)' if plan else 'none'}",
        f"Current workout streak: {stats.current_streak_days} days",
    ]
    if stats.weight_change_kg is not None:
        lines.append(f"Weight change over 30 days: {stats.weight_change_kg} kg")
    return "\n".join(lines)
def build_system_prompt(db: Session, user: User) -> str:
    """Fixed rules + fresh data, rebuilt on every message so the numbers are never stale."""
    return f"{SYSTEM_PROMPT}\n\nUser data (live):\n{build_user_context(db, user)}"
# ------------------------------------------------------------------ greeting (first message, no AI call)
def greeting_word(local_hour: Optional[int]) -> str:
    if local_hour is None:
        return "Hi"
    if local_hour < 12:
        return "Good morning"
    if local_hour < 18:
        return "Good afternoon"
    return "Good evening"
def build_greeting(db: Session, user: User, local_hour: Optional[int]) -> str:
    """'Good morning djihane! You're at 68% of today's goal...' built from a template (free and instant)."""
    percent = build_home(db, user).today_progress.percent
    name = user.username or ""
    word = greeting_word(local_hour)
    if percent == 0:
        return f"{word} {name}! No workout logged yet today. Want a quick tip to get started?".replace("  ", " ")
    return f"{word} {name}! You're at {percent}% of today's goal 🔥 want a quick tip to close it out?".replace("  ", " ")
# ------------------------------------------------------------------ reading the chat
def list_messages(db: Session, user_id: int, limit: int = 100) -> List[ChatMessage]:
    """Last `limit` messages, oldest first (the order the screen displays them)."""
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))
def user_messages_today(db: Session, user_id: int) -> int:
    start, end = day_bounds()
    return (
        db.query(func.count(ChatMessage.id))
        .filter(ChatMessage.user_id == user_id,
                ChatMessage.role == "user",
                ChatMessage.created_at >= start,
                ChatMessage.created_at < end)
        .scalar()
        or 0
    )
 
 
def to_api_messages(history: List[ChatMessage], new_text: str) -> List[dict]:
    """
    Converts DB rows into the format the Claude API expects.
    The API requires the conversation to START with a 'user' message, but our chat
    starts with the coach's greeting. So if the first message is from the coach,
    we put a short placeholder user message before it: the greeting stays in context
    and 'yes, give me a tip' makes sense.
    """
    messages = [{"role": m.role, "content": m.content} for m in history]
    if messages and messages[0]["role"] == "assistant":
        messages.insert(0, {"role": "user", "content": "Hi coach"})
    messages.append({"role": "user", "content": new_text})
    return messages
# ------------------------------------------------------------------ writing the chat
def start_conversation(db: Session, user: User, local_hour: Optional[int]) -> List[ChatMessage]:
    """Opens the screen: if the chat is empty, the coach sends the greeting first."""
    existing = list_messages(db, user.id)
    if existing:
        return existing
    db.add(ChatMessage(user_id=user.id, role="assistant", content=build_greeting(db, user, local_hour)))
    db.commit()
    return list_messages(db, user.id)
 
 
def ask_coach(db: Session, user: User, text: str) -> Tuple[ChatMessage, ChatMessage]:
    """
    The main function: user sends a message -> Claude answers.
    Both messages are saved ONLY if Claude answered, so a failed call leaves no orphan message.
    """
    if user_messages_today(db, user.id) >= MAX_USER_MESSAGES_PER_DAY:
        raise CoachLimitReached()
 
    history = list_messages(db, user.id, MAX_HISTORY_MESSAGES)
    try:
        response = get_client().messages.create(
            model=COACH_MODEL,
            max_tokens=MAX_REPLY_TOKENS,
            system=build_system_prompt(db, user),
            messages=to_api_messages(history, text),
        )
    except (APIError, RuntimeError) as exc:
        raise CoachUnavailable() from exc
    reply_text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not reply_text:
        raise CoachUnavailable()
    user_msg = ChatMessage(user_id=user.id, role="user", content=text)
    coach_msg = ChatMessage(user_id=user.id, role="assistant", content=reply_text)
    db.add_all([user_msg, coach_msg])
    db.commit()
    db.refresh(user_msg)
    db.refresh(coach_msg)
    return user_msg, coach_msg
def clear_history(db: Session, user_id: int) -> None:
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()
 