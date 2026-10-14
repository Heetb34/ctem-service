
from sqlalchemy import Column, Integer, String, TIMESTAMP, JSON, text

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    report_name = Column(String(100), nullable=False)

    report_type = Column(String(50), nullable=False)

    generated_by = Column(String(100), nullable=False)

    # Stores the actual generated report as structured JSON.
    report_data = Column(JSON, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )
