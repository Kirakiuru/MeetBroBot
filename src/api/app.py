"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.api.routes import schedule, meetings, settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="MeetBroBot API",
        version="0.2.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    # CORS — allow Telegram WebApp origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Telegram WebApp runs in iframe
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(schedule.router, prefix="/api")
    app.include_router(meetings.router, prefix="/api")
    app.include_router(settings.router, prefix="/api")

    # Health check
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Serve static frontend (built files)
    static_dir = Path(__file__).parent.parent.parent / "webapp" / "dist"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
