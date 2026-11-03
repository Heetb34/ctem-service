from sqlalchemy import Column, Integer, String, JSON, TIMESTAMP, text

from app.database import Base


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    template_id = Column(String(100), nullable=True)
    parameters = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=False)

    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )