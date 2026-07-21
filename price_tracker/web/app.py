from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..config import settings
from ..repository import backfill_unit_prices, ensure_database, import_input, list_categories, mark_running_jobs_interrupted
from .routes import router


def create_app(db_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        ensure_database(app.state.db_path)
        mark_running_jobs_interrupted(app.state.db_path)
        backfill_unit_prices(app.state.db_path)
        if settings.categories_dir.exists() and not list_categories(app.state.db_path):
            import_input(settings.categories_dir, app.state.db_path)
        yield

    app = FastAPI(title="Price Tracker", lifespan=lifespan)
    app.state.db_path = db_path or settings.database_path
    app.include_router(router)

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


app = create_app()
