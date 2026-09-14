from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, text
from app.database import Base


class ExceptionManagement(Base):
    __tablename__ = "exceptions"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    exposure_id = Column(Integer, nullable=False)

    exception_reason = Column(Text, nullable=False)

    approved_by = Column(String(100), nullable=True)

    exception_status = Column(String(30), default="Pending")

    expiry_date = Column(Date, nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )