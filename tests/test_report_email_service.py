from pathlib import Path

from app.services import report_email_service as email_service


def test_gmail_smtp_configuration_builds_tls_email(monkeypatch, tmp_path):
    state = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            state.update(host=host, port=port, timeout=timeout)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            state["tls"] = True

        def login(self, username, password):
            state["login"] = (username, password)

        def send_message(self, message):
            state["message"] = message
            return {}

    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_FROM", "sender@example.com")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_USERNAME", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-app-password")
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    attachment = tmp_path / "report.csv"
    attachment.write_text("summary\nready\n", encoding="utf-8")

    email_service.send_report_email(
        recipients=["recipient@example.com"],
        report_name="Weekly report",
        file_path=attachment,
    )

    assert state["host"] == "smtp.gmail.com"
    assert state["port"] == 587
    assert state["tls"] is True
    assert state["login"] == ("sender@example.com", "test-app-password")
    assert state["message"]["To"] == "recipient@example.com"
    attachment_part = next(state["message"].iter_attachments())
    assert attachment_part.get_filename() == "report.csv"
