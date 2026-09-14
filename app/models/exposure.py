from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from app.database import Base


class Exposure(Base):
    __tablename__ = "exposures"

    id = Column(Integer, primary_key=True, index=True)

    cycle_id = Column(Integer, nullable=False)

    asset_name = Column(String(100), nullable=False)

    vulnerability = Column(String(255), nullable=False)

    severity = Column(String(20), nullable=False)

    risk_score = Column(Integer, nullable=False)

    status = Column(String(30), default="Discovered")

    # C-08 Prioritization
    priority = Column(String(20), default="Pending")
    priority_score = Column(Integer, default=0)

    # Beta POD Data
    asset_id = Column(String(50), nullable=True)
    beta_risk_rating = Column(Integer, default=0)
    business_criticality = Column(String(20), nullable=True)

    # Audit Fields
    created_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP")
    )

    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP")
    )