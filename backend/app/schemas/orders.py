from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

OrderStatus = Literal["PENDING", "ACCEPTED", "PREPARING", "READY", "DELIVERED"]
OrderSize = Literal["S", "M", "L"]
MilkPreference = Literal["WHOLE", "OAT", "ALMOND", "LACTOSE_FREE", "NONE"]


class OrderCreateRequest(BaseModel):
    shop_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    size: OrderSize = "M"
    sugar_level: int = Field(default=0, ge=0, le=5)
    milk_preference: MilkPreference = "WHOLE"
    extra_shots: int = Field(default=0, ge=0, le=3)


class QrPayload(BaseModel):
    order_id: UUID
    user_id: UUID
    shop_id: UUID
    created_at: str
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class OrderResponse(BaseModel):
    id: int
    order_id: UUID
    user_id: int
    shop_id: int
    shop_name: str
    product_id: int
    product_name: str
    status: OrderStatus
    customizations: OrderCreateRequest
    created_at: str
    qr_code: QrPayload
    qr_code_json: str
    remaining_credits: int


class ShopOrderResponse(OrderResponse):
    customer_name: str | None
    customer_phone: str


class OrderStatusUpdateRequest(BaseModel):
    status: Literal["ACCEPTED", "PREPARING", "READY"]


class QrVerificationResponse(BaseModel):
    verified: bool
    message: str
    order_id: UUID
    status: OrderStatus
