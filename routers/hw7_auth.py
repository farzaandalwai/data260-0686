import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from database import get_db
from models import User


router = APIRouter(prefix="/auth")
bearer = HTTPBearer(auto_error=False)
TOKEN_MINUTES = 60


class LoginRequest(BaseModel):
    username: str
    password: str


def token_secret():
    value = os.getenv("JWT_SECRET")
    if not value:
        raise RuntimeError("JWT_SECRET is not configured")
    return value


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: DbSession = Depends(get_db),
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        claims = jwt.decode(credentials.credentials, token_secret(), algorithms=["HS256"])
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_roles(*roles):
    def check(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Role not permitted")
        return user

    return check


@router.post("/login")
def login(data: LoginRequest, db: DbSession = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == data.username))
    valid = user is not None and bcrypt.checkpw(data.password.encode(), user.password_hash.encode())
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=TOKEN_MINUTES)},
        token_secret(),
        algorithm="HS256",
    )
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "role": user.role}}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}
