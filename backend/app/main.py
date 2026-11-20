from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.orders import router as orders_router
from app.api.routes.roles import router as roles_router
from app.api.routes.shops import router as shops_router
from app.db.session import create_tables
from app.models import Order, Product, Shop, Subscription, User


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    create_tables()
    yield


app = FastAPI(title="KahveCell API", lifespan=lifespan)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(shops_router, prefix="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=PlainTextResponse)
def home() -> str:
    return "çalışıyor"
