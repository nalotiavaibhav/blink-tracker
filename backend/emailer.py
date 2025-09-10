"""Minimal SMTP email sender (works with AWS SES SMTP as well).

Configure via env:
- SMTP_HOST (e.g., email-smtp.ap-south-1.amazonaws.com)
- SMTP_PORT (default 587)
- SMTP_USER
- SMTP_PASSWORD
- SMTP_FROM (e.g., WaW <no-reply@yourdomain.com>)
- SMTP_TLS (true/false, default true)
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    host = os.getenv("SMTP_HOST")
    if not host:
        raise RuntimeError("SMTP_HOST not configured")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "no-reply@example.com"))
    use_tls = os.getenv("SMTP_TLS", "true").lower() in ("1", "true", "yes")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if use_tls:
        with smtplib.SMTP(host, port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as smtp:
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
