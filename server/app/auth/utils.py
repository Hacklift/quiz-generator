import random

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

from server.app.db.core.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_otp():

    return str(random.randint(100000, 999999))


def generate_verification_token(email: str) -> str:

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)

    payload = {"sub": email, "exp": expire}

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_verification_token(token: str):

    try:

        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITHM)

        return payload["sub"]

    except jwt.ExpiredSignatureError:

        raise HTTPException(status_code=400, detail="Token expired")

    except jwt.InvalidTokenError:

        raise HTTPException(status_code=400, detail="Invalid token")


def hash_token(token: str) -> str:

    return pwd_context.hash(token)


def verify_token_hash(plain_token: str, hashed_token: str) -> bool:

    return pwd_context.verify(plain_token, hashed_token)


def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)) -> str:

    if not settings.JWT_SECRET:

        raise ValueError("JWT_SECRET is not set")


    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode.update({

        "exp": expire,

        "jti": str(uuid.uuid4())

    })

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:

    if not settings.JWT_SECRET:

        raise ValueError("JWT_SECRET is not set")


    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)


    jti = str(uuid.uuid4())

    to_encode.update({

        "exp": expire,

        "jti": jti,

        "type": "refresh"

    })


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


def decode_token(token: str):

    try:

        return jwt.decode(token, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    except jwt.PyJWTError:

        return None
