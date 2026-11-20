from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import JWT_ALGORITHM, JWT_SECRET_KEY
from app.db.session import SessionLocal, get_db
from app.models import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz veya süresi dolmuş erişim anahtarı.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise unauthorized
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None or not user.is_verified or payload.get("role") != user.role:
        raise unauthorized
    return user


def get_current_user_for_stream(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    with SessionLocal() as db:
        return get_current_user(credentials, db)


def require_roles(*roles: str) -> Callable[..., User]:
    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için rolünüz yeterli değil.",
            )
        return user

    return check_role
