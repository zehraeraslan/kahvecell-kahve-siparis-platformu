import json
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import Order, Product, RefreshSession, Shop, Subscription, User


def read_sse_event(lines):
    event_type = None
    data = []
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        if not line:
            if event_type is not None:
                return event_type, json.loads("\n".join(data))
            continue
        if line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data.append(line.removeprefix("data:").strip())
    raise AssertionError("SSE stream ended before an event arrived.")


class OrderFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        suffix = uuid4().hex[:8]
        self.customer_phone = f"05{str(uuid4().int)[:9]}"
        self.owner_phone = f"05{str(uuid4().int)[:9]}"
        self.customer_name = f"Customer-{suffix}"
        with SessionLocal.begin() as session:
            self.customer = User(
                phone_number=self.customer_phone,
                full_name=self.customer_name,
                role="CUSTOMER",
                is_verified=True,
            )
            self.owner = User(
                phone_number=self.owner_phone,
                role="SHOP_OWNER",
                is_verified=True,
            )
            session.add_all([self.customer, self.owner])
            session.flush()
            self.customer_id = self.customer.id
            self.owner_id = self.owner.id
            self.shop = Shop(
                name=f"OrderTestShop-{suffix}",
                address="Kızılay, Ankara",
                latitude=39.9208,
                longitude=32.8541,
                owner_user_id=self.owner_id,
                is_active=True,
            )
            session.add(self.shop)
            session.flush()
            self.shop_id = self.shop.id
            self.product = Product(
                shop_id=self.shop_id,
                name=f"OrderTestCoffee-{suffix}",
                description="Test coffee",
                price_kurus=10000,
                is_available=True,
            )
            session.add(self.product)
            session.flush()
            self.product_id = self.product.id
            self.subscription = Subscription(
                user_id=self.customer_id,
                plan_type="STARTER",
                remaining_credits=2,
                status="ACTIVE",
            )
            session.add(self.subscription)
            session.flush()
            self.subscription_id = self.subscription.id

        self.customer_headers = {
            "Authorization": f"Bearer {create_access_token(self.customer_id, 'CUSTOMER')}"
        }
        self.owner_headers = {
            "Authorization": f"Bearer {create_access_token(self.owner_id, 'SHOP_OWNER')}"
        }

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        with SessionLocal.begin() as session:
            session.execute(delete(Order).where(Order.user_id == self.customer_id))
            session.execute(
                delete(Subscription).where(Subscription.id == self.subscription_id)
            )
            session.execute(
                delete(Product).where(Product.id == self.product_id)
            )
            session.execute(delete(Shop).where(Shop.id == self.shop_id))
            session.execute(
                delete(RefreshSession).where(
                    RefreshSession.user_id.in_([self.customer_id, self.owner_id])
                )
            )
            session.execute(
                delete(User).where(User.id.in_([self.customer_id, self.owner_id]))
            )

    def test_credit_qr_order_status_and_owner_access(self) -> None:
        order_payload = {
            "shop_id": self.shop_id,
            "product_id": self.product_id,
            "size": "M",
            "sugar_level": 1,
            "milk_preference": "OAT",
            "extra_shots": 1,
        }
        created = self.client.post(
            "/api/v1/orders",
            headers=self.customer_headers,
            json=order_payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        order = created.json()
        self.assertEqual(order["remaining_credits"], 1)
        self.assertEqual(order["shop_name"], self.shop.name)
        customer_shop_orders = self.client.get(
            "/api/v1/orders/shop",
            headers=self.customer_headers,
        )
        self.assertEqual(customer_shop_orders.status_code, 403)
        self.assertEqual(
            set(order["qr_code"]),
            {"order_id", "user_id", "shop_id", "created_at", "signature"},
        )
        self.assertEqual(len(order["qr_code"]["signature"]), 64)
        self.assertEqual(
            self.client.get(
                "/api/v1/orders/history",
                headers=self.customer_headers,
            ).json()[0]["id"],
            order["id"],
        )
        unauthenticated_events = self.client.get(
            f"/api/v1/orders/{order['id']}/events"
        )
        self.assertEqual(unauthenticated_events.status_code, 401)
        owner_orders = self.client.get(
            "/api/v1/orders/shop",
            headers=self.owner_headers,
        ).json()
        self.assertEqual(owner_orders[0]["id"], order["id"])
        self.assertEqual(owner_orders[0]["customer_name"], self.customer_name)
        self.assertEqual(owner_orders[0]["customer_phone"], self.customer_phone)

        with self.client.stream(
            "GET",
            f"/api/v1/orders/{order['id']}/events",
            headers=self.customer_headers,
        ) as events:
            self.assertEqual(events.status_code, 200)
            self.assertEqual(
                events.headers["content-type"],
                "text/event-stream; charset=utf-8",
            )
            event_lines = iter(events.iter_lines())
            event_type, initial_event = read_sse_event(event_lines)
            self.assertEqual(event_type, "order_status")
            self.assertEqual(initial_event["status"], "PENDING")

            invalid_transition = self.client.patch(
                f"/api/v1/orders/{order['id']}/status",
                headers=self.owner_headers,
                json={"status": "PREPARING"},
            )
            self.assertEqual(invalid_transition.status_code, 409)
            for next_status in ("ACCEPTED", "PREPARING", "READY"):
                updated = self.client.patch(
                    f"/api/v1/orders/{order['id']}/status",
                    headers=self.owner_headers,
                    json={"status": next_status},
                )
                self.assertEqual(updated.status_code, 200, updated.text)
                self.assertEqual(updated.json()["status"], next_status)

                event_type, event = read_sse_event(event_lines)
                self.assertEqual(event_type, "order_status")
                self.assertEqual(event["status"], next_status)

            altered_qr = {**order["qr_code"], "signature": "0" * 64}
            invalid_qr = self.client.post(
                "/api/v1/orders/verify-qr",
                headers=self.owner_headers,
                json=altered_qr,
            )
            self.assertEqual(invalid_qr.status_code, 400)

            redeemed = self.client.post(
                "/api/v1/orders/verify-qr",
                headers=self.owner_headers,
                json=order["qr_code"],
            )
            self.assertEqual(redeemed.status_code, 200, redeemed.text)
            self.assertTrue(redeemed.json()["verified"])
            self.assertEqual(redeemed.json()["status"], "DELIVERED")

            event_type, event = read_sse_event(event_lines)
            self.assertEqual(event_type, "order_status")
            self.assertEqual(event["status"], "DELIVERED")

        self.assertEqual(
            self.client.get(
                f"/api/v1/orders/{order['id']}",
                headers=self.customer_headers,
            ).json()["status"],
            "DELIVERED",
        )

        repeated_qr = self.client.post(
            "/api/v1/orders/verify-qr",
            headers=self.owner_headers,
            json=order["qr_code"],
        )
        self.assertEqual(repeated_qr.status_code, 409)

        with SessionLocal.begin() as session:
            subscription = session.get(Subscription, self.subscription_id)
            subscription.remaining_credits = 0
        no_credits = self.client.post(
            "/api/v1/orders",
            headers=self.customer_headers,
            json=order_payload,
        )
        self.assertEqual(no_credits.status_code, 409)

        with SessionLocal.begin() as session:
            subscription = session.get(Subscription, self.subscription_id)
            subscription.status = "CANCELLED"
        no_subscription = self.client.post(
            "/api/v1/orders",
            headers=self.customer_headers,
            json=order_payload,
        )
        self.assertEqual(no_subscription.status_code, 403)

        with SessionLocal.begin() as session:
            subscription = session.get(Subscription, self.subscription_id)
            subscription.status = "ACTIVE"
            subscription.remaining_credits = -1
        unlimited_order = self.client.post(
            "/api/v1/orders",
            headers=self.customer_headers,
            json=order_payload,
        )
        self.assertEqual(unlimited_order.status_code, 201)
        self.assertEqual(unlimited_order.json()["remaining_credits"], -1)


if __name__ == "__main__":
    unittest.main()
