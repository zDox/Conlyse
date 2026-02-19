from __future__ import annotations

import smtplib
import ssl
from email.mime.text import MIMEText

from app.core.config import settings


def send_2fa_code(to_address: str, code: str) -> None:
    """Send a 2FA verification code via SMTP.

    Raises:
        RuntimeError: If the email could not be sent.
    """
    msg = MIMEText(
        f"Your Conlyse verification code is: {code}\n\nThis code expires in 5 minutes.",
        "plain",
    )
    msg["Subject"] = "Conlyse – Your verification code"
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
