from dotenv import load_dotenv
load_dotenv()

import asyncio

from app.routers import prioritization
from app.routers import exposure
from app.database import Base, engine
from app.models.exposure import Exposure
from fastapi import FastAPI
from sqlalchemy import text
from app.models.validation_plan import ValidationPlan
from app.routers import validation_plan
from app.database import engine
from app.routers import validation_schedule
from app.routers import remediation
from app.routers import exception
from app.routers import report
from app.routers import trend
from app.models.schedule import Schedule
from app.routers import schedule
from app.models.framework_mapping import FrameworkMapping
from app.routers import framework_mapping
from app.models.report_schedule import ReportSchedule
from app.routers import report_schedule
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.report_scheduler_runner import run_due_report_schedules
from app.services.exposure_outbox_publisher import publish_exposure_outbox

from app.models.report_job import ReportJob
from app.models.saved_report import SavedReport
from app.models.outbox_event import OutboxEvent
from app.routers import saved_report

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CTEM Service",
    version="1.0.0"
)
scheduler = BackgroundScheduler()
outbox_stop = asyncio.Event()
outbox_task = None


@app.on_event("startup")
def start_report_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            run_due_report_schedules,
            trigger="interval",
            seconds=30,
            id="report_schedule_checker",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        print("Report scheduler started. Checking every 30 seconds.")


@app.on_event("startup")
async def start_exposure_event_publisher():
    global outbox_task
    outbox_stop.clear()
    outbox_task = asyncio.create_task(publish_exposure_outbox(outbox_stop))


@app.on_event("shutdown")
def stop_report_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("Report scheduler stopped.")


@app.on_event("shutdown")
async def stop_exposure_event_publisher():
    outbox_stop.set()
    if outbox_task is not None:
        outbox_task.cancel()
        try:
            await outbox_task
        except asyncio.CancelledError:
            pass
        
app.include_router(report_schedule.router)
app.include_router(exposure.router)
app.include_router(prioritization.router)
app.include_router(validation_plan.router)
app.include_router(validation_schedule.router)
app.include_router(remediation.router)
app.include_router(exception.router)
app.include_router(saved_report.router)
app.include_router(report.router)
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
