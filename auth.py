from fastapi import HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from database import get_db
from hash import verify_password
from auth_utils import create_access_token
import schemas
from models import User
from schemas import user_create, userout
from hash import hash_password, verify_password
import os
import smtplib
from email.mime.text import MIMEText
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse
import random
from datetime import datetime, timedelta
from schemas import ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest
router = APIRouter(prefix="/auth", tags=["auth"])
# ---------------------------------------------------------------------------
# Email helper
# ---------------------------------------------------------------------------
def send_reset_email(to_email: str, code: str):
    """
    Sends the reset code by email via SMTP.
    Configure these env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    (For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, use an App Password.)
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password]):
        # Fallback for local dev if SMTP isn't configured yet
        print(f"[DEV] SMTP not configured. Reset code for {to_email}: {code}")
        return

    subject = "Your password reset code"
    body = f"Your verification code is: {code}\nIt expires in 10 minutes."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())
    except Exception as e:
        # Don't leak SMTP errors to the client (avoid email enumeration / info leak)
        print(f"Failed to send reset email to {to_email}: {e}")


# ---------------------------------------------------------------------------
# Login / Register
# ---------------------------------------------------------------------------
@router.post("/login")
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", response_model=userout)
def sign_up(user_n: user_create, db: Session = Depends(get_db)):
    user_ext = db.query(User).filter(User.email == user_n.email).first()
    if user_ext:
        raise HTTPException(status_code=400, detail="email already exists")
    new_User = User(
        fullname=user_n.fullname,
        email=user_n.email,
        hashed_password=hash_password(user_n.password),
        provider="local"
    )
    db.add(new_User)
    db.commit()
    db.refresh(new_User)
    return new_User
# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")

    email = user_info["email"]
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            fullname=user_info.get("name", ""),
            email=email,
            hashed_password=None,
            provider="google",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # was only defined in the "if not user" branch before — bug fix
    access_token = create_access_token({"sub": str(user.id)})

    frontend_url = os.getenv("FRONTEND_URL")
    return RedirectResponse(f"{frontend_url}/oauth-success?token={access_token}")


# ---------------------------------------------------------------------------
# Forgot / verify / reset password
# (these were accidentally nested inside google_callback before — now top-level)
# ---------------------------------------------------------------------------
@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        # Don't reveal whether the email exists (avoid email enumeration attack)
        # — return the same message in every case
        return {"message": "If this email exists, a code has been sent"}

    code = str(random.randint(1000, 9999))  # 4-digit code
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    send_reset_email(user.email, code)

    return {"message": "If this email exists, a code has been sent"}


@router.post("/verify-code")
def verify_code(request: VerifyCodeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.reset_code:
        raise HTTPException(status_code=400, detail="Invalid request")

    if user.reset_code != request.code:
        raise HTTPException(status_code=400, detail="Incorrect code")

    if datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(status_code=400, detail="Code expired, request a new one")

    return {"message": "Code verified"}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not user.reset_code:
        raise HTTPException(status_code=400, detail="Invalid request")

    if user.reset_code != request.code:
        raise HTTPException(status_code=400, detail="Incorrect code")

    if datetime.utcnow() > user.reset_code_expires:
        raise HTTPException(status_code=400, detail="Code expired, request a new one")

    user.hashed_password = hash_password(request.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()

    return {"message": "Password reset successful"}