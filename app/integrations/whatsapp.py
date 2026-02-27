"""WhatsApp integration — MOCK for MVP.

Replace this module with a real Twilio/WhatsApp Business API client later.
The interface is intentionally simple so it can be swapped without changing callers.
"""

import logging

logger = logging.getLogger(__name__)


def send_whatsapp(*, target: str, message: str) -> dict:
    """Send a WhatsApp message (MOCK — logs to console).

    Args:
        target: Phone number or identifier for the recipient.
        message: Message body.

    Returns:
        A dict with delivery metadata (mock).
    """
    logger.info(
        "[MOCK WHATSAPP] To: %s | Message: %s",
        target,
        message[:200],
    )
    return {
        "status": "sent_mock",
        "target": target,
        "message": message,
    }
