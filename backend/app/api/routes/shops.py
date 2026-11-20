from math import asin, cos, radians, sin, sqrt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Product, Shop
from app.schemas.shops import ProductResponse, ShopDetailResponse, ShopResponse

router = APIRouter(prefix="/shops", tags=["Dükkânlar"])
EARTH_RADIUS_KM = 6371.0
DEFAULT_RADIUS_KM = 10.0


def distance_in_kilometers(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_delta = radians(latitude_b - latitude_a)
    longitude_delta = radians(longitude_b - longitude_a)
    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(radians(latitude_a))
        * cos(radians(latitude_b))
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        name=product.name,
        description=product.description,
        price_kurus=product.price_kurus,
        price_tl=product.price_kurus / 100,
        is_available=product.is_available,
    )


def shop_response(shop: Shop, distance_km: float | None = None) -> ShopResponse:
    return ShopResponse(
        id=shop.id,
        name=shop.name,
        address=shop.address,
        latitude=shop.latitude,
        longitude=shop.longitude,
        opening_hours=shop.opening_hours,
        rating=shop.rating,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
    )


@router.get("", response_model=list[ShopResponse])
def list_shops(
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    search: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
) -> list[ShopResponse]:
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422,
            detail="Yakınlık araması için latitude ve longitude birlikte gönderilmelidir.",
        )
    if radius_km is not None and latitude is None:
        raise HTTPException(
            status_code=422,
            detail="radius_km kullanmak için latitude ve longitude da gönderin.",
        )

    statement = select(Shop).where(Shop.is_active.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        statement = statement.where(
            or_(Shop.name.ilike(term), Shop.address.ilike(term))
        )
    shops = list(db.scalars(statement))

    if latitude is None or longitude is None:
        return [shop_response(shop) for shop in sorted(shops, key=lambda item: item.name.casefold())]

    radius = radius_km if radius_km is not None else DEFAULT_RADIUS_KM
    nearby = [
        (
            shop,
            distance_in_kilometers(
                latitude, longitude, shop.latitude, shop.longitude
            ),
        )
        for shop in shops
    ]
    nearby = [item for item in nearby if item[1] <= radius]
    nearby.sort(key=lambda item: (item[1], item[0].name.casefold()))
    return [shop_response(shop, distance) for shop, distance in nearby]


@router.get("/{shop_id}/menu", response_model=list[ProductResponse])
def get_shop_menu(shop_id: int, db: Session = Depends(get_db)) -> list[ProductResponse]:
    shop = db.get(Shop, shop_id)
    if shop is None or not shop.is_active:
        raise HTTPException(status_code=404, detail="Dükkân bulunamadı.")
    products = db.scalars(
        select(Product)
        .where(Product.shop_id == shop_id, Product.is_available.is_(True))
        .order_by(Product.name)
    )
    return [product_response(product) for product in products]


@router.get("/{shop_id}", response_model=ShopDetailResponse)
def get_shop_detail(shop_id: int, db: Session = Depends(get_db)) -> ShopDetailResponse:
    shop = db.scalar(
        select(Shop)
        .options(selectinload(Shop.products))
        .where(Shop.id == shop_id, Shop.is_active.is_(True))
    )
    if shop is None:
        raise HTTPException(status_code=404, detail="Dükkân bulunamadı.")
    summary = shop_response(shop)
    return ShopDetailResponse(
        **summary.model_dump(),
        menu=[
            product_response(product)
            for product in sorted(shop.products, key=lambda item: item.name.casefold())
            if product.is_available
        ],
    )
