from contextlib import asynccontextmanager

from fastapi import FastAPI

from bede_data.api.analytics import router as analytics_router
from bede_data.api.config_api import router as config_router
from bede_data.api.freshness import router as freshness_router
from bede_data.api.goals import router as goals_router
from bede_data.api.health import router as health_router
from bede_data.api.location import router as location_router
from bede_data.api.memories import router as memories_router
from bede_data.api.retention import router as retention_router
from bede_data.api.sessions import router as sessions_router
from bede_data.api.storage import router as storage_router
from bede_data.api.task_log import router as task_log_router
from bede_data.api.vault_data import router as vault_data_router
from bede_data.api.vault_queue import router as vault_queue_router
from bede_data.api.weather import router as weather_router
from bede_data.db.connection import init_db
from bede_data.ingest.router import router as ingest_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="bede-data", lifespan=lifespan)
    app.include_router(ingest_router)
    app.include_router(health_router)
    app.include_router(vault_data_router)
    app.include_router(location_router)
    app.include_router(weather_router)
    app.include_router(memories_router)
    app.include_router(goals_router)
    app.include_router(task_log_router)
    app.include_router(config_router)
    app.include_router(analytics_router)
    app.include_router(sessions_router)
    app.include_router(vault_queue_router)
    app.include_router(freshness_router)
    app.include_router(storage_router)
    app.include_router(retention_router)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
