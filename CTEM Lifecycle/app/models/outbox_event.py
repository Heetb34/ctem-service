from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, func

from app.database import Base


class OutboxEvent(Base):
    """CTEM event committed atomically with the source exposure."""

    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(36), nullable=False, unique=True, index=True)
    topic = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, server_default=func.now())
    lease_until = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
