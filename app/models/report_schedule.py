from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    TIMESTAMP,
    text,
)

from app.database import Base


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)
    report_name = Column(String(100), nullable=False)
    report_type = Column(String(50), nullable=False)

    # Supported schedule types will be validated by the API.
    frequency = Column(String(20), nullable=False)
    start_at = Column(DateTime, nullable=False)

    # Example: ["security-team@example.com"]
    recipients = Column(JSON, nullable=True)

    # pdf, csv, or xlsx
    report_format = Column(String(10), nullable=False, default="pdf")

    enabled = Column(Boolean, nullable=False, default=True)

    created_by = Column(String(100), nullable=False)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )