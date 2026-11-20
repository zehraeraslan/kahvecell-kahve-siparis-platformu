import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.main import app
from app.models import Payment, RefreshSession, Subscription, User


class BillingFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        self.phone_number = "05" + str(uuid4().int)[:9]
        self.client.post(
            "/api/v1/auth/register",
            json={
                "phone_number": self.phone_number,
                "full_name": "Test Kullanıcı",
                "password": "TestPass123!",
            },
        ).raise_for_status()
        token_response = self.client.post(
            "/api/v1/auth/verify-otp",
            json={"phone_number": self.phone_number, "code": "1234"},
        )
        token_response.raise_for_status()
        access_token = token_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {access_token}"}

    def test_password_login_and_invalid_password(self) -> None:
        invalid_login = self.client.post(
            "/api/v1/auth/login",
            json={
                "phone_number": self.phone_number,
                "password": "WrongPass123!",
            },
        )
        self.assertEqual(invalid_login.status_code, 401)

        valid_login = self.client.post(
            "/api/v1/auth/login",
            json={
                "phone_number": self.phone_number,
                "password": "TestPass123!",
            },
        )
        self.assertEqual(valid_login.status_code, 200, valid_login.text)
        self.assertIn("access_token", valid_login.json())

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        with SessionLocal.begin() as session:
            user = session.scalar(
                select(User).where(User.phone_number == self.phone_number)
            )
            if user is not None:
                session.execute(delete(Payment).where(Payment.user_id == user.id))
                session.execute(
                    delete(Subscription).where(Subscription.user_id == user.id)
                )
                session.execute(
                    delete(RefreshSession).where(RefreshSession.user_id == user.id)
                )
                session.delete(user)

    def test_purchase_upgrade_and_cancel(self) -> None:
        plans = self.client.get("/api/v1/subscriptions/plans")
        self.assertEqual(plans.status_code, 200)
        self.assertEqual(
            [plan["monthly_price_kurus"] for plan in plans.json()],
            [8999, 14999, 24999],
        )

        failed_payment = self.client.post(
            "/api/v1/payments/process",
            headers=self.headers,
            json={
                "plan_type": "STARTER",
                "card_number": "4000-0000-0000-0002",
            },
        )
        self.assertFalse(failed_payment.json()["success"])
        rejected_subscription = self.client.post(
            "/api/v1/subscriptions",
            headers=self.headers,
            json={"transaction_id": failed_payment.json()["transaction_id"]},
        )
        self.assertEqual(rejected_subscription.status_code, 402)

        starter_payment = self.client.post(
            "/api/v1/payments/process",
            headers=self.headers,
            json={
                "plan_type": "STARTER",
                "card_number": "4242-4242-4242-4242",
            },
        )
        started = self.client.post(
            "/api/v1/subscriptions",
            headers=self.headers,
            json={"transaction_id": starter_payment.json()["transaction_id"]},
        )
        self.assertEqual(started.status_code, 201)
        self.assertEqual(started.json()["remaining_credits"], 10)

        premium_payment = self.client.post(
            "/api/v1/payments/process",
            headers=self.headers,
            json={"plan_type": "PREMIUM", "card_number": "4242424242424242"},
        )
        upgraded = self.client.patch(
            "/api/v1/subscriptions/me",
            headers=self.headers,
            json={
                "plan_type": "PREMIUM",
                "transaction_id": premium_payment.json()["transaction_id"],
            },
        )
        self.assertEqual(upgraded.status_code, 200)
        self.assertEqual(upgraded.json()["remaining_credits"], 20)
        self.assertEqual(upgraded.json()["guest_rights"], 2)

        cancelled = self.client.delete(
            "/api/v1/subscriptions/me",
            headers=self.headers,
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["status"], "CANCELLED")


if __name__ == "__main__":
    unittest.main()
