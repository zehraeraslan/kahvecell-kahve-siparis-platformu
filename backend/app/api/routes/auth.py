from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_roles
from app.core.passwords import hash_password, verify_password
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
from app.db.session import get_db
from app.models import RefreshSession, User
from app.schemas.auth import (
    OtpSentResponse,
    OtpVerificationRequest,
    PasswordLoginRequest,
    ProfileUpdateRequest,
    RegistrationRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Kullanıcı ve kimlik doğrulama"])
SIMULATED_OTP = "1234"


def issue_tokens(user: User, db: Session) -> TokenResponse:
    refresh_token = create_refresh_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )
    access_token = create_access_token(user.id, user.role)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
        profile_complete=bool(user.full_name),
        user=user,
    )


@router.post(
    "/register",
    response_model=OtpSentResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegistrationRequest,
    db: Session = Depends(get_db),
) -> OtpSentResponse:
    user = db.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if user is not None and user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu numara zaten kayıtlı. Giriş için /auth/login kullanın.",
        )
    if user is None:
        user = User(
            phone_number=payload.phone_number,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role="CUSTOMER",
        )
        db.add(user)
    else:
        user.full_name = payload.full_name.strip()
        user.password_hash = hash_password(payload.password)
    db.commit()
    return OtpSentResponse(
        message="Doğrulama kodu simülasyon olarak hazırlandı.",
        phone_number=payload.phone_number,
        development_otp=SIMULATED_OTP,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: PasswordLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon numarası veya şifre hatalı.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Numara henüz doğrulanmadı. Önce kayıt akışını tamamlayın.",
        )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telefon numarası veya şifre hatalı.",
        )
    result = issue_tokens(user, db)
    db.commit()
    db.refresh(user)
    return result


@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(
    payload: OtpVerificationRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    if payload.code != SIMULATED_OTP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doğrulama kodu hatalı.",
        )
    user = db.scalar(
        select(User).where(User.phone_number == payload.phone_number)
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Numara kayıtlı değil. Önce kayıt olun.",
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Numara zaten doğrulanmış. Giriş için telefon ve şifre kullanın.",
        )
    user.is_verified = True
    result = issue_tokens(user, db)
    db.commit()
    db.refresh(user)
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    refresh_session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_refresh_token(payload.refresh_token)
        )
    )
    if (
        refresh_session is None
        or refresh_session.revoked_at is not None
        or refresh_session.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token geçersiz, iptal edilmiş veya süresi dolmuş.",
        )
    user = db.get(User, refresh_session.user_id)
    if user is None or not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı hesabı etkin değil.",
        )
    refresh_session.revoked_at = now
    result = issue_tokens(user, db)
    db.commit()
    db.refresh(user)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    db.commit()


@router.get("/me", response_model=UserResponse)
def get_profile(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Güncellenecek en az bir profil alanı gönderin.",
        )
    for field, value in changes.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


