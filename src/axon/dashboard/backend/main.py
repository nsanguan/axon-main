#!/usr/bin/env python3
"""Axon Control Tower — Dashboard server entry point.

Usage:
    python -m axon.dashboard.backend.main
    # or
    uvicorn axon.dashboard.backend.app:create_app --reload --port 8000
"""

from __future__ import annotations

import uvicorn

from axon.dashboard.backend.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "axon.dashboard.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
