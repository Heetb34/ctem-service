from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, text
from app.database import Base


class ValidationPlan(Base):
    __tablename__ = "validation_plans"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    exposure_id = Column(Integer, nullable=False)

    validation_type = Column(String(100), nullable=False)

    validation_status = Column(String(30), default="Planned")

    assigned_to = Column(String(100), nullable=True)

    planned_date = Column(Date, nullable=True)

    remarks = Column(Text, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )