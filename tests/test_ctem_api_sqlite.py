from fastapi import FastAPI
from fastapi.testclient import TestClient
import csv
from io import StringIO
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (  # noqa: F401
    exception as exception_model,
    exposure as exposure_model,
    framework_mapping,
    outbox_event,
    remediation,
    report,
    report_job,
    report_schedule,
    saved_report,
    schedule as schedule_model,
    validation_plan,
)
from app.models.exception import ExceptionManagement
from app.models.exposure import Exposure
from app.models.remediation import RemediationTracking
from app.models.validation_plan import ValidationPlan
from app.routers import (
    exception,
    exposure,
    prioritization,
    remediation as remediation_router,
    report as report_router,
    schedule,
    trend,
    validation_plan as validation_plan_router,
    validation_schedule,
)


def test_ctem_api_lifecycle_against_isolated_sqlite_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    app = FastAPI()
    for router in (
        exposure.router,
        prioritization.router,
        validation_plan_router.router,
        validation_schedule.router,
        remediation_router.router,
        exception.router,
        trend.router,
        schedule.router,
        report_router.router,
    ):
        app.include_router(router)

    def override_get_db():
        with test_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    inputs = [
        {"asset_name": "Web Server", "vulnerability": "SQL Injection", "severity": "Critical", "risk_score": 92},
        {"asset_name": "API Gateway", "vulnerability": "Broken Auth", "severity": "High", "risk_score": 78},
        {"asset_name": "HR Portal", "vulnerability": "XSS", "severity": "Medium", "risk_score": 55},
        {"asset_name": "Intranet", "vulnerability": "Info Disclosure", "severity": "Low", "risk_score": 20},
    ]

    created = []
    for payload in inputs:
        response = client.post("/ctem/cycles/1/exposures", json=payload)
        assert response.status_code == 200
        created.append(response.json())

    tenant_id = "cb92ef51-d121-4ef6-9a9c-a4b353f9bf63"
    event_response = client.post(
        "/ctem/cycles/99/exposures",
        json={
            "asset_name": "Event Source", "vulnerability": "CVE-TEST",
            "severity": "Critical", "risk_score": 99,
            "tenant_id": tenant_id, "user_id": "test-recipient",
        },
    )
    assert event_response.status_code == 200

    with Session(engine) as db:
        assert db.query(Exposure).filter(Exposure.cycle_id == 1).count() == 4
        outbox_row = db.query(outbox_event.OutboxEvent).one()
        assert outbox_row.topic == "exposure-events"
        assert outbox_row.payload["tenant_id"] == tenant_id
        assert outbox_row.payload["severity"] == "critical"

    priorities = client.post("/ctem/cycles/1/prioritize")
    assert priorities.status_code == 200
    assert [row["priority"] for row in priorities.json()] == [
        "Critical", "High", "Medium", "Low"
    ]

    plans = client.post("/ctem/cycles/1/validation-plan")
    assert plans.status_code == 200
    assert len(plans.json()) == 2

    schedule_response = client.post(
        "/ctem/schedule",
        json={
            "cycle_name": "SQLite Demo",
            "frequency": "daily",
            "start_date": "2026-10-27",
            "status": "Active",
        },
    )
    assert schedule_response.status_code == 200
    assert client.get("/ctem/schedule").json()[0]["cycle_name"] == "SQLite Demo"

    validation_schedule_response = client.post(
        "/ctem/cycles/1/validation-schedule",
        json={"assigned_to": "tester", "planned_date": "2026-10-30"},
    )
    assert validation_schedule_response.status_code == 200
    assert all(
        row["validation_status"] == "Scheduled"
        for row in validation_schedule_response.json()
    )

    remediation_response = client.post(
        "/ctem/cycles/1/remediation",
        json={
            "assigned_to": "engineer",
            "remediation_status": "In Progress",
            "completion_date": None,
            "remediation_notes": "Test-only record",
        },
    )
    assert remediation_response.status_code == 200
    assert len(remediation_response.json()) == 2

    with Session(engine) as db:
        db.add(
            ExceptionManagement(
                cycle_id=1,
                exposure_id=created[0]["id"],
                exception_reason="Accepted in isolated test",
                exception_status="Pending",
            )
        )
        db.commit()
        assert db.query(ValidationPlan).count() == 2
        assert db.query(RemediationTracking).count() == 2

    exceptions = client.get("/ctem/cycles/1/exceptions")
    assert exceptions.status_code == 200
    assert len(exceptions.json()) == 1

    trends = client.get("/ctem/cycles/1/trends")
    assert trends.status_code == 200
    assert trends.json() == {
        "cycle_id": 1,
        "total_exposures": 4,
        "critical": 1,
        "high": 1,
        "medium": 1,
        "low": 1,
        "average_risk_score": 61.25,
    }

    templates = client.get("/ctem/reports/templates")
    assert templates.status_code == 200
    assert len(templates.json()) == 25

    report_response = client.post(
        "/ctem/cycles/1/report",
        json={
            "report_name": "SQLite lifecycle report",
            "report_type": "cycle-summary",
            "generated_by": "test",
        },
    )
    assert report_response.status_code == 201
    report_id = report_response.json()["id"]
    assert report_response.json()["report_data"]["summary"]["total_exposures"] == 4

    csv_export = client.get(f"/ctem/reports/{report_id}/export?format=csv")
    assert csv_export.status_code == 200
    rows = list(csv.reader(StringIO(csv_export.content.decode("utf-8-sig"))))
    assert ["summary", "", "total_exposures", "4"] in rows

    pdf_export = client.get(f"/ctem/reports/{report_id}/export?format=pdf")
    assert pdf_export.status_code == 200
    assert pdf_export.content.startswith(b"%PDF-")

    excel_export = client.get(f"/ctem/reports/{report_id}/export?format=xlsx")
    assert excel_export.status_code == 200
    assert excel_export.content.startswith(b"PK\x03\x04")
