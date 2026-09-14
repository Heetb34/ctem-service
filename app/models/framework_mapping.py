from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from app.database import Base


class FrameworkMapping(Base):
    __tablename__ = "framework_mappings"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    framework_name = Column(String(100), nullable=False)

    control_name = Column(String(255), nullable=False)

    status = Column(String(30), default="Mapped")

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )