"""Control Tower — FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from axon.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and clean up application resources."""
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application with routes and middleware."""
    app = FastAPI(
        title="Axon Control Tower",
        description="Strategic Administration Dashboard for Axon ASCP",
        version="0.0.2",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Prometheus metrics instrumentation
    Instrumentator().instrument(app).expose(app)

    # Register routers
    from axon.dashboard.backend.escalation_api import router as escalation_router
    from axon.dashboard.backend.routes import router

    app.include_router(router, prefix="/api")
    app.include_router(escalation_router)

    return app
