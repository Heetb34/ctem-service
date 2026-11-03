from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_recipients(recipients):
    if recipients is None:
        return None

    normalized = []
    for recipient in recipients:
        address = recipient.strip()
        if not _EMAIL_PATTERN.fullmatch(address):
            raise ValueError(f"Invalid email address: {recipient!r}")
        if address not in normalized:
            normalized.append(address)
    return normalized


class ReportScheduleRequest(BaseModel):
    cycle_id: int
    report_name: str
    report_type: str

    frequency: Literal[
        "once",
        "daily",
        "weekly",
        "monthly",
        "quarterly",
    ]

    start_at: datetime

    recipients: list[str] = Field(default_factory=list)

    report_format: Literal["pdf", "csv", "xlsx"] = "pdf"

    enabled: bool = True
    created_by: str

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, recipients):
        return _validate_recipients(recipients)


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    report_name: str
    report_type: str
    frequency: str
    start_at: datetime
    recipients: list[str] | None = None
    delivered_recipients: list[str] | None = None
    report_format: str
    enabled: bool
    created_by: str
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    attempts: int = 0
    last_error: str | None = None
    last_report_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReportScheduleUpdate(BaseModel):
    frequency: Literal[
        "once",
        "daily",
        "weekly",
        "monthly",
        "quarterly",
    ] | None = None

    start_at: datetime | None = None
    recipients: list[str] | None = None
    report_format: Literal["pdf", "csv", "xlsx"] | None = None
    enabled: bool | None = None

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, recipients):
        return _validate_recipients(recipients)
