
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


logger = logging.getLogger(__name__)


class PartialEmailDeliveryError(RuntimeError):
    """SMTP accepted some recipients and explicitly refused the rest."""

    def __init__(self, accepted_recipients: list[str], refused_recipients: list[str]):
        self.accepted_recipients = accepted_recipients
        self.refused_recipients = refused_recipients
        super().__init__(
            "SMTP refused recipient(s): " + ", ".join(refused_recipients)
        )


def send_report_email(
    recipients: list[str],
    report_name: str,
    file_path: str | Path,
) -> None:
    """Email a generated report to its configured recipients."""
    if not recipients:
        return

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", smtp_username or "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {
        "1", "true", "yes"
    }

    if not smtp_host or not sender:
        raise RuntimeError(
            "Email is not configured. Set SMTP_HOST and SMTP_FROM."
        )

    attachment_path = Path(file_path)

    if not attachment_path.is_file():
        raise FileNotFoundError(
            f"Report file not found: {attachment_path}"
        )

    message = EmailMessage()
    message["Subject"] = f"CTEM Report: {report_name}"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(
        f"Your scheduled CTEM report '{report_name}' is attached."
    )

    suffix = attachment_path.suffix.lower()
    if suffix == ".pdf":
        maintype, subtype = "application", "pdf"
    elif suffix == ".csv":
        maintype, subtype = "text", "csv"
    elif suffix == ".xlsx":
        maintype, subtype = (
            "application",
            "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        raise ValueError(
            f"Unsupported attachment type: {suffix}"
        )

    message.add_attachment(
        attachment_path.read_bytes(),
        maintype=maintype,
        subtype=subtype,
        filename=attachment_path.name,
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        if use_tls:
            server.starttls()

        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)

        refused = server.send_message(message)

    if refused:
        refused_recipients = list(refused)
        accepted_recipients = [
            recipient for recipient in recipients
            if recipient not in refused
        ]
        raise PartialEmailDeliveryError(
            accepted_recipients=accepted_recipients,
            refused_recipients=refused_recipients,
        )

    logger.info(
        "Report email sent to %s for %s",
        recipients,
        report_name,
    )
