from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
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

    frequency = Column(String(20), nullable=False)
    start_at = Column(DateTime, nullable=False)

    recipients = Column(JSON, nullable=True)
    # Addresses already accepted by SMTP for the current scheduled run.
    delivered_recipients = Column(JSON, nullable=True)
    report_format = Column(String(10), nullable=False, default="pdf")
    enabled = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=False)

    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)

    # Failure tracking for the current run.
    attempts = Column(Integer, nullable=False, default=0, server_default=text("0"))
    last_error = Column(Text, nullable=True)
    # Report already generated for this run, kept so an email retry does not create a duplicate.
    last_report_id = Column(Integer, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )
