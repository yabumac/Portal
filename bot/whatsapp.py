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
import logging
import os
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


def _get_token() -> Optional[str]:
    return os.getenv("WHATSAPP_TOKEN") or WHATSAPP_TOKEN


def _get_phone_id() -> Optional[str]:
    return os.getenv("PHONE_NUMBER_ID") or PHONE_NUMBER_ID


def _messages_url() -> str:
    version = os.getenv("GRAPH_API_VERSION", GRAPH_API_VERSION)
    phone_id = _get_phone_id()
    return f"https://graph.facebook.com/{version}/{phone_id}/messages"


def _headers() -> dict:
    token = _get_token()
    return {
        "Authorization": f"Bearer {token}",
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
    is_mock = os.getenv("MOCK_SEND", "").strip().lower() in ("1", "true", "yes") or MOCK_SEND
    if is_mock:
        logger.info("[MOCK_SEND] would POST to Meta:\n%s", json.dumps(payload, indent=2, ensure_ascii=False))
        return _MockResponse()

    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        err_msg = (
            "WhatsApp credentials not configured! "
            f"WHATSAPP_TOKEN={'configured' if token else 'MISSING'}, "
            f"PHONE_NUMBER_ID={'configured' if phone_id else 'MISSING'}"
        )
        logger.error(err_msg)
        try:
            from bot import db
            db.log_activity("system", "whatsapp_missing_credentials", err_msg)
        except Exception:
            pass
        raise RuntimeError(err_msg)

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(_messages_url(), headers=_headers(), json=payload)

    to_user = payload.get("to", "unknown")
    if response.status_code >= 400:
        logger.error("Meta send failed: %s - %s", response.status_code, response.text)
        try:
            from bot import db
            db.log_activity(to_user, "meta_send_error", f"HTTP {response.status_code}: {response.text}")
        except Exception:
            pass
    else:
        logger.info("Meta send ok (%s): %s", response.status_code, response.text[:500])
        try:
            from bot import db
            msg_type = payload.get("type", "message")
            db.log_activity(to_user, "meta_send_ok", f"Type: {msg_type}")
        except Exception:
            pass

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
) -> Optional[httpx.Response]:
    """
    Send a media message by link.
    Guarantees non-crashing behavior if URL is local or invalid.
    """
    if media_type not in {"image", "video", "audio", "document"}:
        raise ValueError(f"Unsupported media type: {media_type!r}")

    # Meta Graph API strictly requires a valid public http(s) URL
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        logger.warning("send_media skipped: '%s' is not an absolute HTTP/HTTPS URL", url)
        return None

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


async def mark_as_read(message_id: str) -> Optional[httpx.Response]:
    """Mark an incoming message as read (good practice for webhooks)."""
    if not message_id:
        return None
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    try:
        return await _post(payload)
    except Exception as exc:
        logger.warning("mark_as_read non-fatal failure: %s", exc)
        return None


def get_connection_status() -> dict:
    """Check configuration status of Meta WhatsApp credentials."""
    token = _get_token() or ""
    phone_id = _get_phone_id() or ""
    verify_token = os.getenv("VERIFY_TOKEN", "local-test")

    masked_token = (
        f"{token[:6]}...{token[-4:]}"
        if len(token) > 10
        else ("Configured" if token else "MISSING")
    )
    masked_phone = (
        f"...{phone_id[-4:]}"
        if len(phone_id) > 4
        else (phone_id or "MISSING")
    )

    return {
        "token_configured": bool(token),
        "phone_configured": bool(phone_id),
        "token_masked": masked_token,
        "phone_id": phone_id,
        "phone_masked": masked_phone,
        "verify_token": verify_token,
        "ready": bool(token and phone_id),
    }


async def send_test_message(to_phone: str) -> dict:
    """Send a live test message to verify Meta API connection and diagnostics."""
    token = _get_token()
    phone_id = _get_phone_id()

    if not token or not phone_id:
        return {
            "success": False,
            "status_code": 0,
            "error": "Missing WhatsApp credentials in environment",
            "hint": "Set WHATSAPP_TOKEN and PHONE_NUMBER_ID in Vercel Project Settings > Environment Variables.",
        }

    cleaned_phone = "".join(ch for ch in str(to_phone) if ch.isdigit())
    if not cleaned_phone:
        return {
            "success": False,
            "status_code": 0,
            "error": "Invalid phone number",
            "hint": "Enter your phone number including country code without '+', e.g. 15551234567.",
        }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": cleaned_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": "EdTech Hub Connection Test: WhatsApp bot is successfully connected! 🎉",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(_messages_url(), headers=_headers(), json=payload)

        data = resp.json() if resp.text else {}
        if resp.status_code < 300:
            return {
                "success": True,
                "status_code": resp.status_code,
                "message": "Message sent successfully!",
                "data": data,
            }
        else:
            err = data.get("error", {})
            code = err.get("code")
            msg = err.get("message", resp.text)
            hint = "Meta API returned an error."
            if code == 190:
                hint = "Access Token Expired: Generate a new Access Token in Meta Developer Portal (WhatsApp > API Setup or System Users) and update WHATSAPP_TOKEN in Vercel."
            elif code == 131030:
                hint = "Recipient Not Allowed: In Meta Developer Portal (WhatsApp > API Setup), add this phone number to the 'To' test recipient list and verify it with the OTP code."
            elif code == 131047:
                hint = "24-Hour Window Expired: Message the bot from your WhatsApp app first (type 'hi') to open the 24-hour window."
            elif code == 100:
                hint = "Invalid Parameter: Check the phone number format (country code + number, e.g. 15551234567)."

            return {
                "success": False,
                "status_code": resp.status_code,
                "code": code,
                "error": msg,
                "hint": hint,
                "data": data,
            }
    except Exception as exc:
        return {
            "success": False,
            "status_code": 0,
            "error": str(exc),
            "hint": "Network error while connecting to Meta Graph API.",
        }
