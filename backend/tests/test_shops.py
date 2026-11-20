import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models import Product, Shop


class ShopEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.client.__enter__()
        suffix = uuid4().hex[:8]
        self.prefix = f"TestCafe{suffix}"
        with SessionLocal.begin() as session:
            near = Shop(
                name=f"{self.prefix} Near",
                address=f"Kızılay, Ankara {suffix}",
                latitude=39.9208,
                longitude=32.8541,
                is_active=True,
            )
            far = Shop(
                name=f"{self.prefix} Far",
                address=f"Çankaya, Ankara {suffix}",
                latitude=39.93,
                longitude=32.86,
                is_active=True,
            )
            session.add_all([near, far])
            session.flush()
            self.shop_ids = [near.id, far.id]
            session.add(
                Product(
                    shop_id=near.id,
                    name="Test Cappuccino",
                    description="Test menu item",
                    price_kurus=14500,
                    is_available=True,
                )
            )

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        with SessionLocal.begin() as session:
            session.execute(delete(Product).where(Product.shop_id.in_(self.shop_ids)))
            session.execute(delete(Shop).where(Shop.id.in_(self.shop_ids)))

    def test_search_distance_sorting_and_shop_menu(self) -> None:
        nearby = self.client.get(
            "/api/v1/shops",
            params={
                "latitude": 39.9208,
                "longitude": 32.8541,
                "radius_km": 5,
                "search": self.prefix,
            },
        )
        self.assertEqual(nearby.status_code, 200)
        self.assertEqual(
            [shop["id"] for shop in nearby.json()],
            [self.shop_ids[0], self.shop_ids[1]],
        )
        self.assertEqual(nearby.json()[0]["distance_km"], 0)

        by_address = self.client.get(
            "/api/v1/shops",
            params={"search": "Kızılay"},
        )
        self.assertTrue(
            any(self.prefix in shop["name"] for shop in by_address.json())
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/shops",
                params={"latitude": 39.9},
            ).status_code,
            422,
        )

        detail = self.client.get(f"/api/v1/shops/{self.shop_ids[0]}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["menu"][0]["price_tl"], 145)
        menu = self.client.get(f"/api/v1/shops/{self.shop_ids[0]}/menu")
        self.assertEqual(menu.status_code, 200)
        self.assertEqual(menu.json()[0]["name"], "Test Cappuccino")


if __name__ == "__main__":
    unittest.main()
