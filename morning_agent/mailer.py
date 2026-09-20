"""Send the email through Resend (HTTP API)."""

from __future__ import annotations

import requests

RESEND_URL = "https://api.resend.com/emails"
TIMEOUT = 30


class MailError(RuntimeError):
    """Error while sending the email through Resend."""


def send_email(api_key: str, sender: str, recipient: str, subject: str, html: str) -> str:
    """Send the email and return the message id assigned by Resend.

    Raises MailError on any problem.
    """
    if not api_key:
        raise MailError("Missing Resend key — set it in Settings.")
    if not sender or not recipient:
        raise MailError("Set the sender and recipient address in Settings.")

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "html": html,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(RESEND_URL, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise MailError(f"Network error while sending through Resend: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise MailError(f"Resend returned HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        return resp.json().get("id", "")
    except ValueError:
        return ""
