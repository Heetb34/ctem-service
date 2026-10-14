from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    TIMESTAMP,
    JSON,
    text,
)

from app.database import Base


class ReportJob(Base):
    __tablename__ = "report_jobs"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(Integer, nullable=False)
    report_name = Column(String(100), nullable=False)
    report_type = Column(String(50), nullable=False)
    report_format = Column(String(10), nullable=False, default="pdf")
    generated_by = Column(String(100), nullable=False)

    filters = Column(JSON, nullable=True)

    status = Column(String(20), nullable=False, default="pending")
    report_id = Column(Integer, nullable=True)
    file_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )