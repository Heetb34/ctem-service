from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, text
from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)

    cycle_name = Column(String(100), nullable=False)

    frequency = Column(String(30), nullable=False)

    start_date = Column(Date, nullable=False)

    status = Column(String(30), default="Active")

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )