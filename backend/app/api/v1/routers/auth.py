"""Authentication routes."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.clients import Client

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    company: str | None = None
    country: str = "NG"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    name: str


class RegisterResponse(BaseModel):
    message: str
    client_id: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    async for db in get_db():
        existing = await db.execute(select(Client).where(Client.email == req.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        client = Client(
            email=req.email,
            name=req.name,
            company=req.company,
            country=req.country,
            hashed_password=hash_password(req.password),
        )
        db.add(client)
        await db.flush()
        await db.refresh(client)

        from app.services.billing import BillingService
        billing = BillingService(db)
        await billing.ensure_wallet(client.id)
        await db.commit()

        return RegisterResponse(
            message="Account created. Welcome fuel is being credited.",
            client_id=str(client.id),
        )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    async for db in get_db():
        result = await db.execute(select(Client).where(Client.email == req.email))
        client = result.scalar_one_or_none()

        if not client or not verify_password(req.password, client.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = create_access_token(data={"sub": str(client.id), "role": "client"})
        return TokenResponse(
            access_token=token,
            client_id=str(client.id),
            name=client.name,
        )
