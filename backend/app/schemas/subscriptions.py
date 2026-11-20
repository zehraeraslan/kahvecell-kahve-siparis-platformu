import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

PlanType = Literal["STARTER", "PREMIUM", "UNLIMITED"]


class PlanResponse(BaseModel):
    plan_type: PlanType
    name: str
    monthly_price_kurus: int
    monthly_price_tl: float
    monthly_credits: int | None
    guest_rights: int
    priority_service: bool


class PaymentRequest(BaseModel):
    plan_type: PlanType
    card_number: str = Field(min_length=16, max_length=23)

    @field_validator("card_number")
    @classmethod
    def normalize_card_number(cls, value: str) -> str:
        normalized = re.sub(r"[\s-]", "", value)
        if not normalized.isdigit() or len(normalized) != 16:
            raise ValueError("Kart numarası 16 rakam olmalıdır.")
        return normalized


class PaymentResponse(BaseModel):
    transaction_id: UUID
    plan_type: PlanType
    amount_kurus: int
    amount_tl: float
    success: bool
    status: Literal["SUCCEEDED", "FAILED"]
    card_last_four: str
    message: str


class PaymentHistoryItem(PaymentResponse):
    created_at: str


class SubscriptionStartRequest(BaseModel):
    transaction_id: UUID


class SubscriptionChangeRequest(BaseModel):
    plan_type: PlanType
    transaction_id: UUID


class SubscriptionResponse(BaseModel):
    id: int
    plan_type: PlanType
    plan_name: str
    monthly_price_tl: float
    remaining_credits: int
    guest_rights: int
    priority_service: bool
    status: Literal["ACTIVE", "PAUSED", "CANCELLED"]
    started_at: str
    expires_at: str | None
