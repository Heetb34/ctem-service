from dotenv import load_dotenv
load_dotenv()

import asyncio

from fastapi import FastAPI
from sqlalchemy import text

from app.database import Base, engine

# Register CTEM database models
from app.models.exposure import Exposure
from app.models.validation_plan import ValidationPlan
from app.models.schedule import Schedule
from app.models.framework_mapping import FrameworkMapping
from app.models.outbox_event import OutboxEvent

# CTEM routers
from app.routers import prioritization
from app.routers import exposure
from app.routers import validation_plan
from app.routers import validation_schedule
from app.routers import remediation
from app.routers import exception
from app.routers import trend
from app.routers import schedule
from app.routers import framework_mapping

# CTEM event publisher
from app.services.exposure_outbox_publisher import publish_exposure_outbox

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CTEM Service",
    version="1.0.0"
)

outbox_stop = asyncio.Event()
outbox_task = None


@app.on_event("startup")
async def start_exposure_event_publisher():
    global outbox_task
    outbox_stop.clear()
    outbox_task = asyncio.create_task(
        publish_exposure_outbox(outbox_stop)
    )


@app.on_event("shutdown")
async def stop_exposure_event_publisher():
    outbox_stop.set()

    if outbox_task is not None:
        outbox_task.cancel()
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass


app.include_router(exposure.router)
app.include_router(prioritization.router)
app.include_router(validation_plan.router)
app.include_router(validation_schedule.router)
app.include_router(remediation.router)
app.include_router(exception.router)
app.include_router(trend.router)
app.include_router(schedule.router)
app.include_router(framework_mapping.router)


@app.get("/")
def home():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "message": "MySQL Connected Successfully!"
    }
