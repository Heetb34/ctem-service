from fastapi import FastAPI

from reporting_engine.database import Base, engine
from reporting_engine.models.report import Report
from reporting_engine.models.report_job import ReportJob
from reporting_engine.models.saved_report import SavedReport

from reporting_engine.routers import report, saved_report


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Reporting Engine",
    description="Independent AEV Reporting Service",
    version="1.0.0",
)

app.include_router(report.router)
app.include_router(saved_report.router)


@app.get("/health")
def health_check():
    return {
        "service": "Reporting Engine",
        "status": "healthy",
    }
