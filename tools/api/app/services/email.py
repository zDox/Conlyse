from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText

from app.core.config import settings


def _send_email(to_address: str, subject: str, body: str) -> None:
    """Internal helper to send an email via SMTP.

    Raises:
        RuntimeError: If the email could not be sent.
    """
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_address

    try:
        if settings.SMTP_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_address, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_FROM, to_address, msg.as_string())
    except Exception as exc:
        raise RuntimeError(f"Failed to send email: {exc}") from exc


def send_2fa_code(to_address: str, code: str) -> None:
    """Send a 2FA verification code via SMTP."""
    _send_email(
        to_address,
        "Conlyse \u2013 Your verification code",
        f"Your Conlyse verification code is: {code}\n\nThis code expires in 5 minutes.",
    )


def send_verification_email(to_address: str, code: str) -> None:
    """Send an account email-verification code via SMTP."""
    _send_email(
        to_address,
        "Conlyse \u2013 Verify your email address",
        (
            f"Welcome to Conlyse!\n\n"
            f"Your email verification code is: {code}\n\n"
            f"This code expires in "
            f"{settings.EMAIL_VERIFICATION_CODE_EXPIRE_SECONDS // 60} minutes.\n\n"
            "If you did not create an account, you can safely ignore this email."
        ),
    )

