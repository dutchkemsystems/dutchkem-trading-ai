"""Dutchkem Fortress Suite — Main FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-layered, monetized SaaS platform for Africa and the global diaspora",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.routers import auth, billing, metering, payments, pills, admin

app.include_router(auth.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(metering.router, prefix="/api/v1")
app.include_router(payments.router, prefix="/api/v1")
app.include_router(pills.afropay_router, prefix="/api/v1")
app.include_router(pills.sentinel_router, prefix="/api/v1")
app.include_router(pills.agent_cloud_router, prefix="/api/v1")
app.include_router(pills.netraid_router, prefix="/api/v1")
app.include_router(pills.trustnode_router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "pillars": {
            "pillar_0": "Agentic Fuel Metering & Billing Engine",
            "pillar_1": "Afro-Pay (Web3 Remittance & Fintech)",
            "pillar_2": "Sentinel Africa (Cybersecurity & SOC)",
            "pillar_3": "African Agent Cloud (Vertical AI Workforce)",
            "pillar_4": "NetraID (Digital Identity & Compliance)",
            "pillar_5": "TrustNode (Open-Weight AI Abstraction)",
        },
    }
