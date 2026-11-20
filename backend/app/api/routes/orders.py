import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.auth import (
    get_current_user,
    get_current_user_for_stream,
    require_roles,
)
from app.core.order_events import OrderEvent, order_event_broker
from app.core.qr_codes import (
    make_qr_payload,
    qr_content,
    qr_core_from_input,
    qr_payload_data,
    verify_qr_signature,
)
from app.db.session import SessionLocal, get_db
from app.models import Order, Product, Shop, Subscription, User
from app.schemas.orders import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    ShopOrderResponse,
    QrPayload,
    QrVerificationResponse,
)

router = APIRouter(prefix="/orders", tags=["Siparişler"])
NEXT_STATUS = {
    "PENDING": "ACCEPTED",
    "ACCEPTED": "PREPARING",
    "PREPARING": "READY",
}


def api_order_status(status_value: str) -> str:
    return "DELIVERED" if status_value == "COMPLETED" else status_value


def order_response(order: Order) -> OrderResponse:
    qr_code = make_qr_payload(order, order.user, order.shop)
    if order.qr_code_token is None or order.qr_code_token != qr_code["signature"]:
        raise HTTPException(
            status_code=500,
            detail="Sipariş QR imzası veritabanındaki kayıtla eşleşmiyor.",
        )
    customizations = json.loads(order.customizations or "{}")
    return OrderResponse(
        id=order.id,
        order_id=order.public_id,
        user_id=order.user_id,
        shop_id=order.shop_id,
        shop_name=order.shop.name,
        product_id=order.product_id,
        product_name=order.product.name,
        status=api_order_status(order.status),
        customizations=OrderCreateRequest(
            shop_id=order.shop_id,
            product_id=order.product_id,
            **customizations,
        ),
        created_at=order.created_at.isoformat(),
        qr_code=QrPayload(**qr_code),
        qr_code_json=qr_content(qr_code),
        remaining_credits=(
            order.subscription.remaining_credits
            if order.subscription is not None
            else 0
        ),
    )


def order_status_event(order: Order) -> OrderEvent:
    return {"order_id": order.id, "status": api_order_status(order.status)}


def sse_status_frame(event: OrderEvent) -> str:
    return (
        "event: order_status\n"
        f"data: {json.dumps(event, separators=(',', ':'))}\n\n"
    )


def load_order(order_id: int, db: Session) -> Order:
    order = db.scalar(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.product),
            selectinload(Order.subscription),
        )
        .where(Order.id == order_id)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Sipariş bulunamadı.")
    return order


def get_active_subscription(user_id: int, db: Session) -> Subscription:
    subscription = db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "ACTIVE",
        )
        .order_by(Subscription.started_at.desc(), Subscription.id.desc())
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if (
        subscription is None
        or subscription.expires_at is not None
        and subscription.expires_at <= now
    ):
        if subscription is not None:
            subscription.status = "CANCELLED"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aktif aboneliğiniz yok. Sipariş vermeden önce bir paket satın alın.",
        )
    if subscription.remaining_credits == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Kahve hakkınız bitmiş. Sipariş için paketinizi yenileyin veya yükseltin.",
        )
    return subscription


def require_shop_owner(shop: Shop, user: User) -> None:
    if shop.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu dükkânın siparişlerini yönetme yetkiniz yok.",
        )


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    shop = db.scalar(
        select(Shop).where(Shop.id == payload.shop_id, Shop.is_active.is_(True))
    )
    product = db.scalar(
        select(Product).where(
            Product.id == payload.product_id,
            Product.shop_id == payload.shop_id,
            Product.is_available.is_(True),
        )
    )
    if shop is None or product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seçilen dükkân veya ürün bulunamadı.",
        )

    subscription = get_active_subscription(user.id, db)
    if subscription.remaining_credits > 0:
        subscription.remaining_credits -= 1

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    customizations = {
        "size": payload.size,
        "sugar_level": payload.sugar_level,
        "milk_preference": payload.milk_preference,
        "extra_shots": payload.extra_shots,
    }
    order = Order(
        user_id=user.id,
        shop_id=shop.id,
        product_id=product.id,
        subscription_id=subscription.id,
        status="PENDING",
        customizations=json.dumps(customizations, separators=(",", ":")),
        created_at=now,
    )
    db.add(order)
    db.flush()
    qr_code = make_qr_payload(order, user, shop)
    order.qr_code_token = qr_code["signature"]
    db.commit()
    return order_response(load_order(order.id, db))


@router.get("/history", response_model=list[OrderResponse])
def order_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrderResponse]:
    orders = db.scalars(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.product),
            selectinload(Order.subscription),
        )
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return [order_response(order) for order in orders]


@router.get("/shop", response_model=list[ShopOrderResponse])
def shop_orders(
    user: User = Depends(require_roles("SHOP_OWNER")),
    db: Session = Depends(get_db),
) -> list[ShopOrderResponse]:
    orders = db.scalars(
        select(Order)
        .join(Shop, Order.shop_id == Shop.id)
        .options(
            selectinload(Order.user),
            selectinload(Order.shop),
            selectinload(Order.product),
            selectinload(Order.subscription),
        )
        .where(Shop.owner_user_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    return [
        ShopOrderResponse(
            **order_response(order).model_dump(),
            customer_name=order.user.full_name,
            customer_phone=order.user.phone_number,
        )
        for order in orders
    ]


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    user: User = Depends(require_roles("SHOP_OWNER")),
    db: Session = Depends(get_db),
) -> OrderResponse:
    order = load_order(order_id, db)
    require_shop_owner(order.shop, user)
    expected_status = NEXT_STATUS.get(order.status)
    if payload.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Bu sipariş için sıradaki durum "
                f"{expected_status or 'yok'} olmalıdır."
            ),
        )
    order.status = payload.status
    db.commit()
    updated_order = load_order(order.id, db)
    order_event_broker.publish(updated_order.id, order_status_event(updated_order))
    return order_response(updated_order)


@router.post("/verify-qr", response_model=QrVerificationResponse)
def verify_and_redeem_qr(
    payload: QrPayload,
    user: User = Depends(require_roles("SHOP_OWNER")),
    db: Session = Depends(get_db),
) -> QrVerificationResponse:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.user), selectinload(Order.shop))
        .where(Order.public_id == str(payload.order_id))
    )
    if order is None:
        raise HTTPException(status_code=404, detail="QR koduna ait sipariş bulunamadı.")
    require_shop_owner(order.shop, user)

    core_payload = qr_core_from_input(payload)
    expected_payload = qr_payload_data(order, order.user, order.shop)
    signature_is_valid = verify_qr_signature(core_payload, payload.signature)
    if (
        core_payload != expected_payload
        or not signature_is_valid
        or order.qr_code_token is None
        or not verify_qr_signature(core_payload, order.qr_code_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR kodu geçersiz veya üzerinde oynanmış.",
        )
    if order.status != "READY":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sipariş teslim için hazır durumda değil veya daha önce teslim edilmiş.",
        )

    order.status = "COMPLETED"
    db.commit()
    order_event_broker.publish(order.id, order_status_event(order))
    return QrVerificationResponse(
        verified=True,
        message="QR kod geçerli; sipariş teslim edildi.",
        order_id=order.public_id,
        status="DELIVERED",
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    order = load_order(order_id, db)
    if order.user_id != user.id and order.shop.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu siparişi görüntüleme yetkiniz yok.",
        )
    return order_response(order)


@router.get("/{order_id}/events")
async def order_status_events(
    order_id: int,
    user: User = Depends(get_current_user_for_stream),
) -> StreamingResponse:
    with SessionLocal() as db:
        order = load_order(order_id, db)
        if order.user_id != user.id and order.shop.owner_user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu siparişin durumunu görüntüleme yetkiniz yok.",
            )

    async def event_stream() -> AsyncIterator[str]:
        queue = await order_event_broker.subscribe(order_id)
        try:
            with SessionLocal() as db:
                latest_order = load_order(order_id, db)
                if (
                    latest_order.user_id != user.id
                    and latest_order.shop.owner_user_id != user.id
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bu siparişin durumunu görüntüleme yetkiniz yok.",
                    )
                initial_event = order_status_event(latest_order)

            yield sse_status_frame(initial_event)
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield sse_status_frame(event)
        finally:
            order_event_broker.unsubscribe(order_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
