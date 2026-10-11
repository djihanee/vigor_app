from fastapi import FastAPI
from database import engine, Base
import auth 
import models
import os
import Strength
import goals
import profile
import activity
import progress
import home
import notification
import Personalinfo 
import coach
from starlette.middleware.sessions import SessionMiddleware
from user import router as users_router
from weight import router as weight_router
from height import router as height_router
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Vega API")
app.include_router(progress.router)
app.include_router(goals.router)
app.include_router(activity.router)
app.include_router(height_router)
app.include_router(auth.router)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY"))
app.include_router(users_router)
app.include_router(weight_router)
app.include_router(profile.router)
app.include_router(home.router)
app.include_router(coach.router)
app.include_router(notification.router)
app.include_router(Personalinfo.router)
app.include_router(Strength.router)
@app.get("/")
def root():
    return {"message": "Vega API is running"}

