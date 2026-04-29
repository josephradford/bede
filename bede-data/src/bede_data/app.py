from contextlib import asynccontextmanager

from fastapi import FastAPI

from bede_data.db.connection import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="bede-data", lifespan=lifespan)

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    return app
