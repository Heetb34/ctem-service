from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.routes import router
from .config import get_settings
from .events import stop_producer
from .logging import configure_logging, log

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_settings().log_level)
    log.info("evidence_repo_starting")
    yield
    await stop_producer()
    log.info("evidence_repo_stopped")

app = FastAPI(title="Evidence Repository", version="0.1.0", lifespan=lifespan)
app.include_router(router)
