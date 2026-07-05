"""Email port + Mailpit SMTP adapter.

In development, Mailpit (http://localhost:8025) catches all outbound email
so nothing is ever delivered to real inboxes.

Usage in production: swap MailpitAdapter for a production adapter
(e.g. SES, Postmark) that implements the same EmailPort Protocol.

GDPR note: email addresses are NOT logged at INFO level to avoid leaking
personal data into structured logs.
"""

from __future__ import annotations

import structlog

from verida.application.ports import EmailPort

logger = structlog.get_logger(__name__)


class MailpitAdapter:
    """Send transactional email via SMTP, captured by Mailpit in development.

    Implements the ``EmailPort`` Protocol.
    """

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 1025,
        from_email: str = "noreply@verida.local",
        username: str = "",
        password: str = "",
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._from_email = from_email
        self._username = username
        self._password = password

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        """Send an email via SMTP.

        Falls back to a log warning if aiosmtplib is not available.
        """
        try:
            import aiosmtplib  # type: ignore[import-untyped]
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self._from_email
            msg["To"] = to_email  # not logged — see GDPR note above

            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._username or None,
                password=self._password or None,
                start_tls=False,
            )

            logger.info("email_sent", subject=subject)

        except ImportError:
            # aiosmtplib not installed — log warning and skip
            logger.warning(
                "email_not_sent_aiosmtplib_missing",
                subject=subject,
                hint="Install aiosmtplib to enable email sending",
            )
        except Exception as exc:
            logger.error(
                "email_send_failed",
                subject=subject,
                error=str(exc),
            )
            raise


class StubEmailAdapter:
    """No-op email adapter for unit tests.

    Records all sent messages in ``sent_messages`` for assertion.
    """

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, str]] = []

    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        self.sent_messages.append(
            {
                "to": to_email,
                "subject": subject,
                "html": body_html,
                "text": body_text,
            }
        )
        logger.debug("stub_email_sent", subject=subject)
