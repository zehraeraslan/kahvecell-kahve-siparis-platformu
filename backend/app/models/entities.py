from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid4())
    )
    phone_number: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="CUSTOMER")
    is_verified: Mapped[bool] = mapped_column(default=False)
    preferences: Mapped[str | None] = mapped_column(Text)
    allergens: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    refresh_sessions: Mapped[list["RefreshSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="refresh_sessions")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('STARTER', 'PREMIUM', 'UNLIMITED')",
            name="ck_subscriptions_plan_type",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'PAUSED', 'CANCELLED')",
            name="ck_subscriptions_status",
        ),
        CheckConstraint("remaining_credits >= -1", name="ck_subscriptions_credits"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_type: Mapped[str] = mapped_column(String(20))
    remaining_credits: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "plan_type IN ('STARTER', 'PREMIUM', 'UNLIMITED')",
            name="ck_payments_plan_type",
        ),
        CheckConstraint(
            "status IN ('SUCCEEDED', 'FAILED')",
            name="ck_payments_status",
        ),
        CheckConstraint("amount_kurus >= 0", name="ck_payments_amount"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_type: Mapped[str] = mapped_column(String(20))
    amount_kurus: Mapped[int] = mapped_column(Integer)
    card_last_four: Mapped[str] = mapped_column(String(4))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id"), unique=True
    )


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid4())
    )
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(150), index=True)
    address: Mapped[str] = mapped_column(String(255))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    opening_hours: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="shop")
    orders: Mapped[list["Order"]] = relationship(back_populates="shop")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("shop_id", "name", name="uq_products_shop_name"),
        CheckConstraint("price_kurus >= 0", name="ck_products_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    price_kurus: Mapped[int] = mapped_column(Integer)
    is_available: Mapped[bool] = mapped_column(default=True)

    shop: Mapped["Shop"] = relationship(back_populates="products")
    orders: Mapped[list["Order"]] = relationship(back_populates="product")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'PREPARING', 'READY', "
            "'COMPLETED', 'CANCELLED')",
            name="ck_orders_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    customizations: Mapped[str | None] = mapped_column(Text)
    qr_code_token: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    user: Mapped["User"] = relationship(back_populates="orders")
    shop: Mapped["Shop"] = relationship(back_populates="orders")
    product: Mapped["Product"] = relationship(back_populates="orders")
    subscription: Mapped["Subscription | None"] = relationship()
