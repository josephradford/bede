from contextlib import asynccontextmanager

from fastapi import FastAPI

from bede_data.api.health import router as health_router
from bede_data.api.vault_data import router as vault_data_router
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

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
