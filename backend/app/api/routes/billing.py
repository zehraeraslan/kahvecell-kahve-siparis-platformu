from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models import Payment, Subscription, User
from app.schemas.subscriptions import (
    PaymentHistoryItem,
    PaymentRequest,
    PaymentResponse,
    PlanResponse,
    SubscriptionChangeRequest,
    SubscriptionResponse,
    SubscriptionStartRequest,
)

router = APIRouter()

PLANS = {
    "STARTER": {
        "name": "Starter",
        "price_kurus": 8999,
        "credits": 10,
        "guest_rights": 0,
        "priority": False,
    },
    "PREMIUM": {
        "name": "Premium",
        "price_kurus": 14999,
        "credits": 20,
        "guest_rights": 2,
        "priority": False,
    },
    "UNLIMITED": {
        "name": "Unlimited",
        "price_kurus": 24999,
        "credits": -1,
        "guest_rights": 5,
        "priority": True,
    },
}

SUCCESS_CARD = "4242424242424242"
FAILURE_CARD = "4000000000000002"


def plan_response(plan_type: str) -> PlanResponse:
    plan = PLANS[plan_type]
    return PlanResponse(
        plan_type=plan_type,
        name=plan["name"],
        monthly_price_kurus=plan["price_kurus"],
        monthly_price_tl=plan["price_kurus"] / 100,
        monthly_credits=None if plan["credits"] == -1 else plan["credits"],
        guest_rights=plan["guest_rights"],
        priority_service=plan["priority"],
    )


def payment_response(payment: Payment) -> PaymentResponse:
    succeeded = payment.status == "SUCCEEDED"
    return PaymentResponse(
        transaction_id=payment.transaction_id,
        plan_type=payment.plan_type,
        amount_kurus=payment.amount_kurus,
        amount_tl=payment.amount_kurus / 100,
        success=succeeded,
        status=payment.status,
        card_last_four=payment.card_last_four,
        message=(
            "Ödeme simülasyonu başarılı."
            if succeeded
            else "Ödeme simülasyonu başarısız."
        ),
    )


def subscription_response(subscription: Subscription) -> SubscriptionResponse:
    plan = PLANS[subscription.plan_type]
    return SubscriptionResponse(
        id=subscription.id,
        plan_type=subscription.plan_type,
        plan_name=plan["name"],
        monthly_price_tl=plan["price_kurus"] / 100,
        remaining_credits=subscription.remaining_credits,
        guest_rights=plan["guest_rights"],
        priority_service=plan["priority"],
        status=subscription.status,
        started_at=subscription.started_at.isoformat(),
        expires_at=(
            subscription.expires_at.isoformat()
            if subscription.expires_at is not None
            else None
        ),
    )


def find_active_subscription(user_id: int, db: Session) -> Subscription | None:
    subscription = db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "ACTIVE",
        )
        .order_by(Subscription.started_at.desc(), Subscription.id.desc())
    )
    if (
        subscription is not None
        and subscription.expires_at is not None
        and subscription.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None)
    ):
        subscription.status = "CANCELLED"
        db.flush()
        return None
    return subscription


def get_paid_transaction(
    transaction_id: UUID,
    plan_type: str,
    user_id: int,
    db: Session,
) -> Payment:
    payment = db.scalar(
        select(Payment).where(Payment.transaction_id == str(transaction_id))
    )
    if payment is None or payment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu kullanıcıya ait ödeme işlemi bulunamadı.",
        )
    if payment.status != "SUCCEEDED":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Başarısız ödeme ile abonelik başlatılamaz.",
        )
    if payment.plan_type != plan_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ödeme işlemi seçilen paketle eşleşmiyor.",
        )
    if payment.subscription_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu ödeme işlemi daha önce kullanılmış.",
        )
    return payment


def create_subscription(
    user_id: int,
    plan_type: str,
    payment: Payment,
    db: Session,
) -> Subscription:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    plan = PLANS[plan_type]
    subscription = Subscription(
        user_id=user_id,
        plan_type=plan_type,
        remaining_credits=plan["credits"],
        status="ACTIVE",
        started_at=now,
        expires_at=now + timedelta(days=30),
    )
    db.add(subscription)
    db.flush()
    payment.subscription_id = subscription.id
    return subscription


@router.get(
    "/subscriptions/plans",
    response_model=list[PlanResponse],
    tags=["Abonelikler"],
)
def list_plans() -> list[PlanResponse]:
    return [plan_response(plan_type) for plan_type in PLANS]


@router.post(
    "/payments/process",
    response_model=PaymentResponse,
    tags=["Ödeme simülasyonu"],
)
def process_payment(
    payload: PaymentRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    card_number = payload.card_number
    succeeded = card_number == SUCCESS_CARD
    if card_number != SUCCESS_CARD and card_number != FAILURE_CARD:
        succeeded = False

    payment = Payment(
        transaction_id=str(uuid4()),
        user_id=user.id,
        plan_type=payload.plan_type,
        amount_kurus=PLANS[payload.plan_type]["price_kurus"],
        card_last_four=card_number[-4:],
        status="SUCCEEDED" if succeeded else "FAILED",
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment_response(payment)


@router.get(
    "/payments/history",
    response_model=list[PaymentHistoryItem],
    tags=["Ödeme simülasyonu"],
)
def payment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentHistoryItem]:
    payments = db.scalars(
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    )
    return [
        PaymentHistoryItem(
            **payment_response(payment).model_dump(),
            created_at=payment.created_at.isoformat(),
        )
        for payment in payments
    ]


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Abonelikler"],
)
def start_subscription(
    payload: SubscriptionStartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    if find_active_subscription(user.id, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zaten aktif aboneliğiniz var; paket değiştirmek için PATCH kullanın.",
        )
    payment = db.scalar(
        select(Payment).where(Payment.transaction_id == str(payload.transaction_id))
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ödeme işlemi bulunamadı.",
        )
    payment = get_paid_transaction(
        payload.transaction_id, payment.plan_type, user.id, db
    )
    subscription = create_subscription(user.id, payment.plan_type, payment, db)
    db.commit()
    db.refresh(subscription)
    return subscription_response(subscription)


@router.get(
    "/subscriptions/me",
    response_model=SubscriptionResponse,
    tags=["Abonelikler"],
)
def get_my_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    subscription = find_active_subscription(user.id, db)
    if subscription is None:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aktif aboneliğiniz bulunmuyor.",
        )
    return subscription_response(subscription)


@router.patch(
    "/subscriptions/me",
    response_model=SubscriptionResponse,
    tags=["Abonelikler"],
)
def change_subscription(
    payload: SubscriptionChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    current = find_active_subscription(user.id, db)
    if current is None:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paket değiştirmek için aktif aboneliğiniz olmalıdır.",
        )
    if current.plan_type == payload.plan_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu paket zaten aktif.",
        )
    payment = get_paid_transaction(payload.transaction_id, payload.plan_type, user.id, db)
    current.status = "CANCELLED"
    subscription = create_subscription(user.id, payload.plan_type, payment, db)
    db.commit()
    db.refresh(subscription)
    return subscription_response(subscription)


@router.post(
    "/subscriptions/me/renew",
    response_model=SubscriptionResponse,
    tags=["Abonelikler"],
)
def renew_subscription(
    payload: SubscriptionStartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    if find_active_subscription(user.id, db) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aboneliğiniz henüz sona ermedi.",
        )
    previous = db.scalar(
        select(Subscription)
        .where(Subscription.user_id == user.id)
        .order_by(Subscription.started_at.desc(), Subscription.id.desc())
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if previous is None or previous.expires_at is None or previous.expires_at > now:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yenilenecek süresi dolmuş abonelik bulunamadı.",
        )
    payment = get_paid_transaction(
        payload.transaction_id, previous.plan_type, user.id, db
    )
    subscription = create_subscription(user.id, previous.plan_type, payment, db)
    db.commit()
    db.refresh(subscription)
    return subscription_response(subscription)


@router.delete(
    "/subscriptions/me",
    response_model=SubscriptionResponse,
    tags=["Abonelikler"],
)
def cancel_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    subscription = find_active_subscription(user.id, db)
    if subscription is None:
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İptal edilecek aktif aboneliğiniz bulunmuyor.",
        )
    subscription.status = "CANCELLED"
    db.commit()
    db.refresh(subscription)
    return subscription_response(subscription)
