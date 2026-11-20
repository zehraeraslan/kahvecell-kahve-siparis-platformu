"""Seed Ankara cafe locations from OpenStreetMap with illustrative menu prices."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.passwords import hash_password
from app.db.session import SessionLocal, create_tables
from app.models import Product, Shop, Subscription, User

DEMO_PHONE = "05550000000"
DEMO_PASSWORD = "KahveTest2026!"
DEMO_SHOP_OWNER_PHONE = "05550000002"
DEMO_SHOP_OWNER_PASSWORD = "DukkanTest2026!"

SHOPS = [
    {
        "name": "Cafe Down Engelsiz Cafe",
        "address": "İzmir 1 Caddesi, Kızılay Mahallesi, Çankaya, Ankara",
        "latitude": 39.9229865,
        "longitude": 32.8539956,
        "prices": (9000, 14500, 11000, 15000),
    },
    {
        "name": "Kocatepe Coffee 1919 Bahçelievler 7.Cadde",
        "address": "70. Sokak, Yukarı Bahçelievler Mahallesi, Çankaya, Ankara",
        "latitude": 39.9219387,
        "longitude": 32.8255133,
        "prices": (9500, 15500, 12000, 16000),
    },
    {
        "name": "Cafe Rosso",
        "address": "66, Tunalı Hilmi Caddesi, Remzi Oğuz Arık Mahallesi, Çankaya, Ankara",
        "latitude": 39.9081500,
        "longitude": 32.8614807,
        "prices": (10000, 16000, 12500, 17000),
    },
    {
        "name": "Nunchi Coffee Co. Çayyolu Nokta",
        "address": "Meksika Caddesi, Ümitköy, Çankaya, Ankara",
        "latitude": 39.9002019,
        "longitude": 32.6923438,
        "prices": (10500, 16500, 13000, 17500),
    },
    {
        "name": "Cafe des Cafes",
        "address": "83, Tunalı Hilmi Caddesi, Barbaros Mahallesi, Çankaya, Ankara",
        "latitude": 39.9066216,
        "longitude": 32.8612044,
        "prices": (9500, 15000, 12000, 16000),
    },
]

PRODUCTS = ("Espresso", "Cappuccino", "Türk kahvesi", "Latte")


def seed() -> None:
    create_tables()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with SessionLocal.begin() as session:
        user = session.scalar(
            select(User).where(User.phone_number == DEMO_PHONE)
        )
        if user is None:
            user = User(
                phone_number=DEMO_PHONE,
                full_name="KahveCell Demo",
                role="CUSTOMER",
                password_hash=hash_password(DEMO_PASSWORD),
                is_verified=True,
            )
            session.add(user)
            session.flush()
        else:
            if user.password_hash is None:
                user.password_hash = hash_password(DEMO_PASSWORD)
            user.is_verified = True

        shop_owner = session.scalar(
            select(User).where(User.phone_number == DEMO_SHOP_OWNER_PHONE)
        )
        if shop_owner is None:
            shop_owner = User(
                phone_number=DEMO_SHOP_OWNER_PHONE,
                full_name="KahveCell Dükkân Sahibi",
                role="SHOP_OWNER",
                password_hash=hash_password(DEMO_SHOP_OWNER_PASSWORD),
                is_verified=True,
            )
            session.add(shop_owner)
            session.flush()
        else:
            shop_owner.role = "SHOP_OWNER"
            shop_owner.is_verified = True
            if shop_owner.password_hash is None:
                shop_owner.password_hash = hash_password(DEMO_SHOP_OWNER_PASSWORD)

        for shop_data in SHOPS:
            shop = session.scalar(
                select(Shop).where(Shop.name == shop_data["name"])
            )
            if shop is None:
                shop = Shop(
                    name=shop_data["name"],
                    address=shop_data["address"],
                    latitude=shop_data["latitude"],
                    longitude=shop_data["longitude"],
                    is_active=True,
                )
                session.add(shop)
                session.flush()
            if shop_data["name"] == "Cafe Down Engelsiz Cafe":
                shop.owner_user_id = shop_owner.id

            for name, price in zip(PRODUCTS, shop_data["prices"], strict=True):
                product = session.scalar(
                    select(Product).where(
                        Product.shop_id == shop.id,
                        Product.name == name,
                    )
                )
                if product is None:
                    session.add(
                        Product(
                            shop_id=shop.id,
                            name=name,
                            description=f"{name} kahve içeceği",
                            price_kurus=price,
                            is_available=True,
                        )
                    )

        starter = session.scalar(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.plan_type == "STARTER",
                Subscription.status == "ACTIVE",
            )
        )
        if starter is None:
            session.add(
                Subscription(
                    user_id=user.id,
                    plan_type="STARTER",
                    remaining_credits=10,
                    status="ACTIVE",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )

    print("Seed verisi hazır.")
    print(f"Demo telefon: {DEMO_PHONE}")
    print(f"Demo şifre: {DEMO_PASSWORD}")
    print(f"Dükkân sahibi demo telefonu: {DEMO_SHOP_OWNER_PHONE} (OTP: 1234)")
    print(f"Dükkân sahibi demo şifresi: {DEMO_SHOP_OWNER_PASSWORD}")
    print("Paket: Aktif Starter (10 kahve hakkı)")
    print("Not: Bu hesap yalnızca yerel test içindir.")
    print("Not: Ürün fiyatları gerçek menü fiyatı değil, yaklaşık demo fiyatıdır.")


if __name__ == "__main__":
    seed()
