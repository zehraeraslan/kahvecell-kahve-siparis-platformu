import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PhoneRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str) -> str:
        normalized = re.sub(r"\D", "", value)
        if not 10 <= len(normalized) <= 15:
            raise ValueError("GSM numarası 10-15 rakam içermelidir.")
        return normalized


class RegistrationRequest(PhoneRequest):
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class PasswordLoginRequest(PhoneRequest):
    password: str = Field(min_length=8, max_length=128)


class OtpVerificationRequest(PhoneRequest):
    code: str = Field(pattern=r"^\d{4}$")


class OtpSentResponse(BaseModel):
    message: str
    phone_number: str
    development_otp: str


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    preferences: str | None = Field(default=None, max_length=2000)
    allergens: str | None = Field(default=None, max_length=1000)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    full_name: str | None
    email: EmailStr | None
    role: Literal["CUSTOMER", "SHOP_OWNER", "ADMIN"]
    preferences: str | None
    allergens: str | None
    is_verified: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    profile_complete: bool
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=200)
