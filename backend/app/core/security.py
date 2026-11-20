import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY backend/.env dosyasında tanımlı olmalıdır.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 15 * 60
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: int, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=ACCESS_TOKEN_EXPIRE_SECONDS
    )
    return jwt.encode(
        {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "exp": expires_at,
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
