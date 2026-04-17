import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import health, generate, review, scripts

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Proviso API",
    version="1.0.0",
    description="AI-powered OCI infrastructure script generation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,   prefix="/api/v1", tags=["Health"])
app.include_router(generate.router, prefix="/api/v1", tags=["Generation"])
app.include_router(review.router,   prefix="/api/v1", tags=["Review"])
app.include_router(scripts.router,  prefix="/api/v1", tags=["Scripts"])
