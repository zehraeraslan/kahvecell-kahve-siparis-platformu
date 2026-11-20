from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_roles
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserResponse

router = APIRouter(tags=["Rol bazlı erişim"])


@router.get("/admin/users", response_model=list[UserResponse])
def list_users(
    _admin: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.get("/shop-owner/dashboard")
def shop_owner_dashboard(
    user: User = Depends(require_roles("SHOP_OWNER")),
) -> dict[str, str]:
    return {
        "message": "Dükkan sahibi erişimi doğrulandı.",
        "phone_number": user.phone_number,
    }
