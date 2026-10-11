from database import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime,Float,ForeignKey,Date,UniqueConstraint,Text
from datetime import datetime, timezone
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    fulname=Column(String)
    email = Column(String,unique=True,index=True)
    hashpassword = Column(String, nullable=True)
    provider = Column(String, default=locals)
    reset_code = Column(String, nullable=True)
    reset_code_expires = Column(DateTime, nullable=True)
    gender = Column(String, nullable=True) 
    age = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    height_cm = Column(Integer, nullable=True)
    goal = Column(String, nullable=True)
    activity_level =Column(String,nullable=True)
class WeightLog(Base):
    __tablename__ = "weight_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    weight_kg = Column(Float, nullable=False)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    calories_burned = Column(Integer, nullable=False)
    duration_min = Column(Integer, nullable=False)
    performed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    time_of_day = Column(String, nullable=False)        # "18:30"
    label = Column(String, nullable=True)               # "Workout time"
    enabled = Column(Boolean, default=True, nullable=False)
class WaterLog(Base):
    __tablename__ = "water_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount_ml = Column(Integer, nullable=False)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
class StepLog(Base):
    __tablename__ = "step_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    steps = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "day", name="one_steps_row_per_day"),)
class SleepLog(Base):
    __tablename__ = "sleep_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)          # the day the user woke up
    minutes = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "day", name="one_sleep_row_per_day"),)
 
 
class FoodLog(Base):
    __tablename__ = "food_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=True)
    calories = Column(Integer, nullable=False)
    logged_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
class WorkoutPlan(Base):
    __tablename__ = "workout_plans"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)           # "Upper body strength"
    exercises_count = Column(Integer, nullable=False)
    duration_min = Column(Integer, nullable=False)
    weekday = Column(Integer, nullable=False) 
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)           # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
class NotificationSettings(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    push_enabled = Column(Boolean, default=True, nullable=False)              # master switch
    # Workout reminders
    daily_workout_reminder = Column(Boolean, default=True, nullable=False)
    daily_reminder_time = Column(String, default="07:00", nullable=False)     # "Every day at 7:00 AM"
    rest_day_checkin = Column(Boolean, default=False, nullable=False)
    missed_workout_alert = Column(Boolean, default=True, nullable=False)
    # Progress & motivation
    streak_reminders = Column(Boolean, default=True, nullable=False)
    weekly_summary = Column(Boolean, default=False, nullable=False)
    ai_coach_messages = Column(Boolean, default=True, nullable=False)
    # General
    app_updates = Column(Boolean, default=False, nullable=False)
class DeviceToken(Base):
    __tablename__ = "device_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String, nullable=False, unique=True)
    platform = Column(String, nullable=False)       # "ios" or "android"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
class UserAvatar(Base):
    __tablename__ = "user_avatars"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    filename = Column(String, nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
class PlanExercise(Base):
    __tablename__ = "plan_exercises"
 
    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False, index=True)
    position = Column(Integer, default=0, nullable=False)       # order on the screen
    name = Column(String, nullable=False)                       # "push-ups"
    sets = Column(Integer, nullable=False)                      # 3
    reps = Column(Integer, nullable=True)                       # 12   (or None for timed exercises)
    duration_sec = Column(Integer, nullable=True)               # 45   (the plank)
 
 
class ExerciseCompletion(Base):
    """One row = 'this user ticked this exercise on this day'."""
    __tablename__ = "exercise_completions"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    exercise_id = Column(Integer, ForeignKey("plan_exercises.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "exercise_id", "day", name="one_tick_per_exercise_per_day"),)
 
 
class PlanCompletion(Base):
    """One row = 'this user finished this plan today' (links to the Workout we logged)."""
    __tablename__ = "plan_completions"  
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False, index=True)
    day = Column(Date, nullable=False)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "plan_id", "day", name="one_completion_per_plan_per_day"),)
