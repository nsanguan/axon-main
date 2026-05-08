"""Control Tower — FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


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
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from axon.dashboard.backend.routes import router
    from axon.dashboard.backend.escalation_api import router as escalation_router

    app.include_router(router, prefix="/api")
    app.include_router(escalation_router)

    return app
