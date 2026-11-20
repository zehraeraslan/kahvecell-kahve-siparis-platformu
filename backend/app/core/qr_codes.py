import hashlib
import hmac
import json
import os
from datetime import timezone
from pathlib import Path

from dotenv import load_dotenv

from app.models import Order, Shop, User
from app.schemas.orders import QrPayload

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

QR_SECRET_KEY = os.getenv("QR_SECRET_KEY")
if not QR_SECRET_KEY:
    raise RuntimeError("QR_SECRET_KEY backend/.env dosyasında tanımlı olmalıdır.")


def qr_payload_data(order: Order, user: User, shop: Shop) -> dict[str, str]:
    created_at = order.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return {
        "order_id": order.public_id,
        "user_id": user.public_id,
        "shop_id": shop.public_id,
        "created_at": created_at.isoformat(),
    }


def create_qr_signature(payload: dict[str, str]) -> str:
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(
        QR_SECRET_KEY.encode("utf-8"),
        canonical_payload,
        hashlib.sha256,
    ).hexdigest()


def make_qr_payload(order: Order, user: User, shop: Shop) -> dict[str, str]:
    payload = qr_payload_data(order, user, shop)
    return {**payload, "signature": create_qr_signature(payload)}


def verify_qr_signature(payload: dict[str, str], signature: str) -> bool:
    return hmac.compare_digest(create_qr_signature(payload), signature)


def qr_content(payload: dict[str, str]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def qr_core_from_input(payload: QrPayload) -> dict[str, str]:
    return {
        "order_id": str(payload.order_id),
        "user_id": str(payload.user_id),
        "shop_id": str(payload.shop_id),
        "created_at": payload.created_at,
    }
