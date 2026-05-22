"""Orchestrator main entrypoint — runs the LangGraph planning cycle with HTTP health endpoint.

Usage:
    python -m axon.orchestrator.main
"""

from __future__ import annotations

import asyncio

from axon.core.config import settings
from axon.core.telemetry import init_telemetry, log_event
from axon.orchestrator.master_graph import MasterGraph


async def main() -> None:
    init_telemetry(settings)
    log_event("info", "orchestrator_starting")

    graph = MasterGraph()
    graph.compile()
    log_event("info", "orchestrator_ready")

    # Lightweight health server using FastAPI
    try:
        from fastapi import FastAPI
        import uvicorn

        app = FastAPI(title="Axon Orchestrator")

        @app.get("/health")
        async def health():
            return {
                "status": "HEALTHY",
                "service": "axon-orchestrator",
                "graph_compiled": graph._compiled is not None,
            }

        @app.get("/")
        async def root():
            return {"service": "axon-orchestrator", "version": "0.0.2"}

        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    except ImportError:
        # Fallback: minimal health server via asyncio
        log_event("warn", "fastapi_not_available", message="Running with minimal health server")
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import threading

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path in ("/health", "/"):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status":"HEALTHY","service":"axon-orchestrator"}')
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        httpd = HTTPServer(("0.0.0.0", 8000), HealthHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            while True:
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
        finally:
            httpd.shutdown()

    finally:
        await graph.close()
        log_event("info", "orchestrator_stopped")


if __name__ == "__main__":
    asyncio.run(main())
