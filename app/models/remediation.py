from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, text
from app.database import Base


class RemediationTracking(Base):
    __tablename__ = "remediation_tracking"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    exposure_id = Column(Integer, nullable=False)

    remediation_status = Column(String(50), default="Pending")

    assigned_to = Column(String(100), nullable=True)

    completion_date = Column(Date, nullable=True)

    remediation_notes = Column(Text, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )