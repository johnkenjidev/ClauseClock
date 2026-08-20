"""
Auth foundation — Stage 1.

Working email/password authentication using JWT access/refresh tokens carried
in httpOnly cookies (a server-side authenticated session).

    user_id is ALWAYS derived server-side from the verified token and NEVER
    accepted from the client (body, query, form or custom header).

Passwords are hashed with bcrypt. This module holds pure helpers; the
`get_current_user` FastAPI dependency lives in server.py where the db handle
is available.
"""

import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 12          # 12h access window
REFRESH_TTL_DAYS = 7


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=True,
        samesite="none", max_age=ACCESS_TTL_MIN * 60, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=True,
        samesite="none", max_age=REFRESH_TTL_DAYS * 86400, path="/",
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie("access_token", path="/", samesite="none", secure=True)
    response.delete_cookie("refresh_token", path="/", samesite="none", secure=True)
