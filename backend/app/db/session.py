from collections.abc import Generator
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).resolve().parents[2] / 'kahvecell.db'}",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(connection, _record) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    missing_columns = {
        "users": {
            "password_hash": "VARCHAR(255)",
            "is_verified": "BOOLEAN NOT NULL DEFAULT 0",
            "allergens": "TEXT",
            "public_id": "VARCHAR(36)",
        },
        "shops": {
            "public_id": "VARCHAR(36)",
            "owner_user_id": "INTEGER REFERENCES users(id)",
        },
        "orders": {
            "public_id": "VARCHAR(36)",
            "subscription_id": "INTEGER REFERENCES subscriptions(id)",
        },
    }
    for table_name, table_columns in missing_columns.items():
        existing_columns = {
            column["name"] for column in inspect(engine).get_columns(table_name)
        }
        for column_name, column_type in table_columns.items():
            if column_name not in existing_columns:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} ADD COLUMN "
                            f"{column_name} {column_type}"
                        )
                    )

    for table_name in ("users", "shops", "orders"):
        with engine.begin() as connection:
            rows = connection.execute(
                text(f"SELECT id FROM {table_name} WHERE public_id IS NULL")
            ).all()
            for row in rows:
                connection.execute(
                    text(f"UPDATE {table_name} SET public_id = :public_id WHERE id = :id"),
                    {"public_id": str(uuid4()), "id": row.id},
                )
            connection.execute(
                text(
                    f"CREATE UNIQUE INDEX IF NOT EXISTS "
                    f"uq_{table_name}_public_id ON {table_name} (public_id)"
                )
            )


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
