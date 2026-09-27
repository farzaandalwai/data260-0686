import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from database import get_db
from models import Session as UserSession
from models import User


COOKIE_NAME = "hw4_session_token"
SESSION_SECONDS = 3600

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_current_user(request: Request, db: DbSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Login required")
    record = db.get(UserSession, token)
    if record is None:
        raise HTTPException(status_code=401, detail="Login required")
    if record.expires_at <= utc_now():
        db.delete(record)
        db.commit()
        raise HTTPException(status_code=401, detail="Login required")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


@router.post("/login")
def login(data: LoginRequest, response: Response, db: DbSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email))
    password_ok = False
    if user is not None:
        password_ok = bcrypt.checkpw(data.password.encode(), user.password_hash.encode())
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = secrets.token_urlsafe(32)
    now = utc_now()
    db.add(
        UserSession(
            id=token,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(seconds=SESSION_SECONDS),
        )
    )
    db.commit()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=SESSION_SECONDS,
    )
    return {
        "message": "Login successful",
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email}


@router.post("/logout")
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        record = db.get(UserSession, token)
        if record is not None:
            db.delete(record)
            db.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"message": "Logged out"}
