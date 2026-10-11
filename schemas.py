from pydantic import BaseModel,EmailStr,field_validator,Field,model_validator
from typing import Literal, Optional
from datetime import datetime,date
from typing import List
from enum import Enum
class FitnessGoal(str, Enum):
    lose_weight = "lose_weight"
    build_muscle = "build_muscle"
    stay_healthy = "stay_healthy"
    general_fitness = "general_fitness"
    cardio_fitness = "cardio_fitness"
    stay_active = "stay_active"
class GoalUpdate(BaseModel):
    goal: FitnessGoal
class GoalOut(BaseModel):
    goal: Optional[FitnessGoal] = None
class user_create(BaseModel):
    fulname:str
    email:EmailStr
    password:str
    password_confirmation:str
@field_validator("password confirmation")
@classmethod
def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v
class userout(BaseModel):
      id:int
      fullname:str
      email:str
class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    very_active = "very_active"
class ActivityUpdate(BaseModel):
    activity_level: ActivityLevel
class ActivityOut(BaseModel):
    activity_level: Optional[ActivityLevel] = None
class GenderUpdate(BaseModel):
    gender: Literal["male", "female"]   
    gender: Optional[str] = None
class ForgotPasswordRequest(BaseModel):
    email: str
class VerifyCodeRequest(BaseModel):
    email: str
    code: str
class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str
class AgeUpdate(BaseModel):
    age: int = Field(..., ge=10, le=100)
class AgeResponse(BaseModel):
    age: int
class WeightOut(BaseModel):
    weight_kg: float
    logged_at: datetime
class WeightSummary(BaseModel):
    current: Optional[float]
    start: Optional[float]
    change: Optional[float]      # current - start (negative = weight lost)
    history: List[WeightOut]
class WeightIn(BaseModel):
    weight_kg: float = Field(..., ge=20, le=300)
class HeightIn(BaseModel):
    height_cm: int = Field(..., ge=50, le=272)   
class HeightOut(BaseModel):
    height_cm: Optional[int]
class WorkoutIn(BaseModel):
    day: date = Field(default_factory=date.today)
    calories_burned: int = Field(gt=0, le=5000)
    duration_min: int = Field(gt=0, le=600)
class WeightIn(BaseModel):
    day: date = Field(default_factory=date.today)
    weight_kg: float = Field(gt=20, lt=400)
class DayCalories(BaseModel):
    label: str            # M T W T F S S
    date: date
    calories: int
    is_today: bool
class CaloriesOut(BaseModel):
    week_start: date
    days: List[DayCalories]
class SummaryOut(BaseModel):
    weight_change_kg: Optional[float]   # e.g. -2.4
    current_streak_days: int
class WeightPoint(BaseModel):
    date: date
    weight_kg: float
class WeightTrendOut(BaseModel):
    points: List[WeightPoint]
    start_label: str = "30d ago"
    end_label: str = "Today"
class ConsistencyDay(BaseModel):
    label: str
    date: date
    done: bool
class ConsistencyOut(BaseModel):
    days: List[ConsistencyDay]
class ProgressOut(BaseModel):
    calories: CaloriesOut
    summary: SummaryOut
    weight_trend: WeightTrendOut
    consistency: ConsistencyOut
Goal = Literal["lose_weight", "build_muscle", "maintain"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active"]
class ProfileStats(BaseModel):
    workouts: int
    day_streak: int
    weight_kg: Optional[float] = None
class GoalProgressOut(BaseModel):
    goal: Optional[str] = None
    percent: Optional[int] = None
class ProfileOut(BaseModel):
    username: Optional[str] = None
    initial: str
    member_since: Optional[date] = None
    stats: ProfileStats
    goal_progress: GoalProgressOut
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[int] = None
    goal: Optional[str] = None
    activity_level: Optional[str] = None
    target_weight_kg: Optional[float] = None
class PersonalInfoUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=40)
    gender: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=10, le=100)
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
class GoalsUpdate(BaseModel):
    goal: Optional[Goal] = None
    activity_level: Optional[ActivityLevel] = None
    target_weight_kg: Optional[float] = Field(default=None, gt=20, lt=400)
class ReminderIn(BaseModel):
    time_of_day: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")   # HH:MM
    label: Optional[str] = None
    enabled: bool = True
class ReminderToggle(BaseModel):
    enabled: bool
class ReminderOut(BaseModel):
    id: int
    time_of_day: str
    label: Optional[str] = None
    enabled: bool
 
    model_config = {"from_attributes": True}
       # lets FastAPI read SQLAlchemy objects
class TodayProgressOut(BaseModel):
    kcal_burned: int
    goal_kcal: int
    percent: int
 
 
class WorkoutPlanIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    exercises_count: int = Field(ge=1, le=50)
    duration_min: int = Field(ge=1, le=300)
    weekday: int = Field(ge=0, le=6)
 
 
class WorkoutPlanOut(BaseModel):
    id: int
    name: str
    exercises_count: int
    duration_min: int
    weekday: int
 
    model_config = {"from_attributes": True}
 
 
class HomeOut(BaseModel):
    username: Optional[str] = None
    today_progress: TodayProgressOut
    calories_left: int
    water_ml: int
    steps: int
    sleep_minutes: int
    todays_workout: Optional[WorkoutPlanOut] = None
 
 
class WaterIn(BaseModel):
    amount_ml: int = Field(gt=0, le=3000)
 
 
class StepsIn(BaseModel):
    steps: int = Field(ge=0, le=100000)
 
 
class SleepIn(BaseModel):
    minutes: int = Field(ge=0, le=1440)
 
 
class FoodIn(BaseModel):
    name: Optional[str] = None
    calories: int = Field(ge=0, le=5000)
class ChatIn(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}
class ChatReplyOut(BaseModel):
    user_message: ChatMessageOut
    reply: ChatMessageOut
class NotificationSettingsOut(BaseModel):
    push_enabled: bool
    daily_workout_reminder: bool
    daily_reminder_time: str
    rest_day_checkin: bool
    missed_workout_alert: bool
    streak_reminders: bool
    weekly_summary: bool
    ai_coach_messages: bool
    app_updates: bool
    model_config = {"from_attributes": True} 
class NotificationSettingsUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    daily_workout_reminder: Optional[bool] = None
    daily_reminder_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")  # HH:MM
    rest_day_checkin: Optional[bool] = None
    missed_workout_alert: Optional[bool] = None
    streak_reminders: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    ai_coach_messages: Optional[bool] = None
    app_updates: Optional[bool] = None
class DeviceTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=500)
    platform: Literal["ios", "android"]
class PersonalInfoOut(BaseModel):
    username: Optional[str] = None
    email: str
    gender: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[int] = None
    weight_kg: Optional[float] = None
    avatar_url: Optional[str] = None
class PersonalInfoIn(BaseModel):
    model_config = {"str_strip_whitespace": True}     # " djihane " -> "djihane"
    username: Optional[str] = Field(default=None, min_length=2, max_length=40)
    email: Optional[str] = Field(default=None, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    gender: Optional[Literal["male", "female", "other"]] = None
    age: Optional[int] = Field(default=None, ge=10, le=100)
    height_cm: Optional[int] = Field(default=None, ge=100, le=250)
    weight_kg: Optional[float] = Field(default=None, ge=20, le=400)
Category = Literal["strength", "cardio", "hiit", "stretching"]
 
 
class ExerciseIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    sets: int = Field(ge=1, le=20)
    reps: Optional[int] = Field(default=None, ge=1, le=200)
    duration_sec: Optional[int] = Field(default=None, ge=5, le=3600)
 
    @model_validator(mode="after")
    def reps_or_duration(self):
        if (self.reps is None) == (self.duration_sec is None):
            raise ValueError("Give either reps or duration_sec (not both, not none)")
        return self
 
 
class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    category: Category = "strength"
    duration_min: int = Field(ge=1, le=300)
    weekday: int = Field(ge=0, le=6)                       # 0 = Monday ... 6 = Sunday
    exercises: List[ExerciseIn] = Field(min_length=1, max_length=30)
 
 
class ExerciseOut(BaseModel):
    id: int
    name: str
    sets: int
    reps: Optional[int] = None
    duration_sec: Optional[int] = None
    label: str                      # "3 sets x 12 reps"
    done: bool
class TodayPlanOut(BaseModel):
    id: int
    name: str
    category: str
    duration_min: int
    exercises_count: int
    status: Literal["scheduled", "in_progress", "completed", "upcoming"]
    weekday: int
    weekday_label: str
    is_today: bool
 
 
 
class TodayWorkoutOut(BaseModel):
    plan: Optional[TodayPlanOut] = None
    exercises: List[ExerciseOut]
    done_count: int
    total_count: int
    next_exercise_id: Optional[int] = None
    coach_tip: str
 
 
class ExerciseDoneIn(BaseModel):
    done: bool
 
 
class WeeklyPlanItem(BaseModel):
    id: int
    name: str
    category: str
    duration_min: int
    exercises_count: int
class WeeklyDayOut(BaseModel):
    weekday: int
    label: str
    date: date
    day_number: int
    is_today: bool
    is_rest_day: bool
    plans: List[WeeklyPlanItem]


class WeeklyOut(BaseModel):
    week_start: date
    planned_days: int
    total_days: int
    summary: str
    days: List[WeeklyDayOut]


class PlanExerciseOut(BaseModel):
    id: int
    name: str
    sets: int
    reps: Optional[int] = None
    duration_sec: Optional[int] = None
    label: str


class PlanDetailOut(BaseModel):
    id: int
    name: str
    category: str
    duration_min: int
    weekday: int
    weekday_label: str
    exercises_count: int
    exercises: List[PlanExerciseOut]
 

class config :
        from_attruibutes=True
