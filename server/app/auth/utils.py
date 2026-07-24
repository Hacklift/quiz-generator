import secrets

import jwt

import os

import uuid

import hashlib

from jwt.exceptions import InvalidTokenError

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from typing import Optional

from dotenv import load_dotenv

from passlib.context import CryptContext

from server.app.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_otp():

    return str(secrets.randbelow(900000) + 100000)


def generate_verification_token(email: str, *, purpose: str = "email_verification") -> str:

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)

    now = datetime.now(timezone.utc)
    payload = {"sub": email, "purpose": purpose, "iat": now, "nbf": now, "exp": expire}

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_verification_token(token: str, *, purpose: str | None = None):

    try:

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if purpose and payload.get("purpose") != purpose:
            raise HTTPException(status_code=400, detail="Invalid token purpose")

        return payload["sub"]

    except jwt.ExpiredSignatureError:

        raise HTTPException(status_code=400, detail="Token expired")

    except jwt.InvalidTokenError:

        raise HTTPException(status_code=400, detail="Invalid token")


def hash_token(token: str) -> str:

    return pwd_context.hash(token)


def verify_token_hash(plain_token: str, hashed_token: str) -> bool:

    return pwd_context.verify(plain_token, hashed_token)


def create_access_token(
    data: dict,
    expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    *,
    session_id: str | None = None,
) -> str:

    if not settings.JWT_SECRET:

        raise ValueError("JWT_SECRET is not set")


    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({

        "exp": expire,
        "iat": now,
        "nbf": now,

        "jti": str(uuid.uuid4()),

        "type": "access",

    })
    if session_id:
        to_encode["sid"] = session_id

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict, *, session_id: str | None = None) -> str:

    if not settings.JWT_SECRET:

        raise ValueError("JWT_SECRET is not set")


    to_encode = data.copy()

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


    jti = str(uuid.uuid4())

    to_encode.update({

        "exp": expire,
        "iat": now,
        "nbf": now,

        "jti": jti,

        "type": "refresh"

    })
    if session_id:
        to_encode["sid"] = session_id


    token = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return token, jti, expire


def decode_refresh_token(token: str) -> dict:

    """Decode and validate refresh token"""

    try:

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


        if payload.get("type") != "refresh":

            raise HTTPException(status_code=401, detail="Invalid token type")


        return payload

    except jwt.ExpiredSignatureError:

        raise HTTPException(status_code=401, detail="Refresh token expired")

    except jwt.InvalidTokenError:

        raise HTTPException(status_code=401, detail="Invalid refresh token")



def verify_password(plain_password, hashed_password):

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):

    return pwd_context.hash(password)


