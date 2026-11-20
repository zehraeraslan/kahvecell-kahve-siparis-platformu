import argparse

from sqlalchemy import select

from app.db.session import SessionLocal, create_tables
from app.models import User

ROLES = ("CUSTOMER", "SHOP_OWNER", "ADMIN")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Yerel test için doğrulanmış bir kullanıcının rolünü ayarla."
    )
    parser.add_argument("phone_number", help="Kullanıcının GSM numarası")
    parser.add_argument("role", choices=ROLES, help="Atanacak rol")
    args = parser.parse_args()

    create_tables()
    phone_number = "".join(character for character in args.phone_number if character.isdigit())
    with SessionLocal.begin() as session:
        user = session.scalar(
            select(User).where(User.phone_number == phone_number)
        )
        if user is None or not user.is_verified:
            parser.error("Önce bu GSM numarasıyla kayıt olup OTP doğrulaması yapın.")
        user.role = args.role

    print(f"{phone_number} kullanıcısının rolü {args.role} olarak ayarlandı.")


if __name__ == "__main__":
    main()
