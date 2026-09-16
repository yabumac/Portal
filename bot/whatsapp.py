"""
bot/whatsapp.py

Thin, async wrappers around the Meta WhatsApp Cloud API (Graph API).

Every outgoing call is made with httpx.AsyncClient. The send helpers are
deliberately picky about Meta's payload limits (3 buttons, 20-char button
titles, 24-char list row titles, 10 rows per section) so a malformed payload
never reaches the Graph API - it gets clipped locally instead.

Config (env vars):
    WHATSAPP_TOKEN  - permanent system-user access token
    PHONE_NUMBER_ID - WhatsApp Business Account phone number id
    GRAPH_API_VERSION (optional, default "v18.0")
"""

import json
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger("whatsapp_bot")

GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v18.0")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
MOCK_SEND = os.getenv("MOCK_SEND", "").strip().lower() in ("1", "true", "yes")

_MAX_BUTTONS = 3
_MAX_BUTTON_TITLE = 20
_MAX_BUTTON_ID = 256
_MAX_ROW_TITLE = 24
_MAX_ROW_ID = 200
_MAX_SECTION_TITLE = 60
_MAX_LIST_TEXT = 20


def _messages_url() -> str:
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def _clip(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len]


class _MockResponse:
    """Stand-in for httpx.Response when MOCK_SEND=1 (local dev without Meta)."""

    def __init__(self, status_code: int = 200, text: str = '{"mock": true}'):
        self.status_code = status_code
        self.text = text

    @property
    def content(self) -> bytes:
        return self.text.encode()


async def _post(payload: dict) -> httpx.Response:
    """POST a payload to the Messages API and log the outcome."""
    if MOCK_SEND:
        logger.info("[MOCK_SEND] would POST to Meta:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))
        return _MockResponse()

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        logger.error("Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID - cannot send")
        raise RuntimeError("WhatsApp credentials not configured")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_messages_url(), headers=_headers(), json=payload)

    if response.status_code >= 400:
        logger.error("Meta send failed: %s - %s", response.status_code, response.text)
    else:
        logger.info("Meta send ok (%s): %s", response.status_code, response.text[:500])
    return response


async def send_text(to: str, body: str) -> httpx.Response:
    """Send a plain text message to a user."""
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body},
    }
    return await _post(payload)


async def send_buttons(
    to: str,
    body: str,
    buttons: list,
    header: Optional[str] = None,
    footer: Optional[str] = None,
) -> httpx.Response:
    """
    Send an interactive button message (max 3 buttons).

    buttons: list of {"id": str, "title": str}. Titles are clipped to 20 chars,
    ids to 256 chars, duplicate ids are dropped.
    """
    cleaned = []
    seen = set()
    for button in buttons[:_MAX_BUTTONS]:
        button_id = _clip(str(button["id"]), _MAX_BUTTON_ID)
        if button_id in seen:
            continue
        seen.add(button_id)
        cleaned.append(
            {
                "type": "reply",
                "reply": {
                    "id": button_id,
                    "title": _clip(str(button["title"]), _MAX_BUTTON_TITLE),
                },
            }
        )

    interactive = {
        "type": "button",
        "body": {"text": _clip(body, 1024)},
        "action": {"buttons": cleaned},
    }
    if header:
        interactive["header"] = {"type": "text", "text": _clip(header, 60)}
    if footer:
        interactive["footer"] = {"text": _clip(footer, 60)}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    return await _post(payload)


async def send_list(
    to: str,
    body: str,
    button_text: str,
    sections: list,
    header: Optional[str] = None,
    footer: Optional[str] = None,
) -> httpx.Response:
    """
    Send an interactive list menu.

    sections: list of {"title": str, "rows": [{"id": str, "title": str}]}.
    Row titles are clipped to 24 chars, ids to 200 chars, max 10 rows per
    section, the list button label to 20 chars.
    """
    validated_sections = []
    for section in sections[:2]:
        cleaned_rows = []
        for row in section.get("rows", [])[:10]:
            cleaned_rows.append(
                {
                    "id": _clip(str(row["id"]), _MAX_ROW_ID),
                    "title": _clip(str(row["title"]), _MAX_ROW_TITLE),
                }
            )
        validated_sections.append(
            {
                "title": _clip(section.get("title", "Options"), _MAX_SECTION_TITLE),
                "rows": cleaned_rows,
            }
        )

    interactive = {
        "type": "list",
        "body": {"text": _clip(body, 1024)},
        "action": {
            "button": _clip(button_text, _MAX_LIST_TEXT),
            "sections": validated_sections,
        },
    }
    if header:
        interactive["header"] = {"type": "text", "text": _clip(header, 60)}
    if footer:
        interactive["footer"] = {"text": _clip(footer, 60)}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": interactive,
    }
    return await _post(payload)


async def send_media(
    to: str,
    media_type: str,
    url: str,
    caption: Optional[str] = None,
    filename: Optional[str] = None,
) -> httpx.Response:
    """
    Send a media message by link.

    media_type: one of "image", "video", "audio", "document".
    filename is only applied to documents; captions are dropped for audio.
    """
    if media_type not in {"image", "video", "audio", "document"}:
        raise ValueError(f"Unsupported media type: {media_type!r}")

    media_payload = {"link": url}
    if media_type == "document" and filename:
        media_payload["filename"] = filename
    if caption and media_type != "audio":
        media_payload["caption"] = caption

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": media_type,
        media_type: media_payload,
    }
    return await _post(payload)


async def mark_as_read(message_id: str) -> httpx.Response:
    """Mark an incoming message as read (good practice for webhooks)."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    return await _post(payload)