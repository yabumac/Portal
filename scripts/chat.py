"""
scripts/chat.py

Local interactive playground for the WhatsApp Learning Bot.

Run (from the project folder):
    python scripts/chat.py

Then just type messages like you would in WhatsApp:
    hi                     -> opens the intro menu (video + Enroll / Ask AI Tutor / AI Self-Assessment)
    enroll                 -> starts the AI for Educators course
    continue               -> after a lesson, continue to the quiz (or tap the button)
    A or B or C            -> answer a quiz / assessment question
    ask_ai_tutor           -> enter AI Tutor mode (with the current lesson context)
    exit                   -> leave AI Tutor mode
    ai_assess              -> start the AI Self-Assessment form
    any other text         -> goes to the AI Tutor (falls back to a canned reply unless you have a GEMINI_API_KEY set)

When the bot shows buttons, just type the label you would tap in WhatsApp.
Type 'q' to quit. The bot replies are printed here instead of being
sent to real WhatsApp, so this NEVER contacts Meta and needs no credentials.
"""

import asyncio
import logging
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.CRITICAL)
os.environ.setdefault("VERIFY_TOKEN", "local-test")

from fastapi.testclient import TestClient  # noqa: E402
from bot import ai_tutor  # noqa: E402
from api import index as app_module  # noqa: E402

FAKE_USER = "1555-test-local"

client = TestClient(app_module.app)

outbox = []
last_turn_buttons = []


async def fake_send_text(to, body):
    outbox.append(("text", body))
    return None


async def fake_send_buttons(to, body, buttons, header=None, footer=None):
    outbox.append(("buttons", buttons, header, body, footer))
    return None


async def fake_send_media(to, media_type, url, caption=None, filename=None):
    outbox.append(("media", media_type, url, caption))
    return None


async def fake_mark_read(message_id):
    return None


async def fake_send_list(*args, **kwargs):
    outbox.append(("list", args, kwargs))
    return None


async def fake_tutor(question, section=""):
    if section:
        return (f"(canned local answer - set GEMINI_API_KEY to get real answers) "
                f"The current lesson block I parsed: {section[:140]}... "
                f"Asked: {question}")
    return ("(canned local answer - set GEMINI_API_KEY to get real answers) "
            f"You asked: {question} - in the AI for Educators course, AI helps "
            "teachers with drafting lessons, generating ideas and giving "
            "feedback, while the teacher stays in charge.")


def print_bot_turn():
    global last_turn_buttons
    if outbox:
        last_turn_buttons = []
    for item in outbox:
        kind = item[0]
        if kind == "text":
            print(f"\n  Bot msg: {item[1]}")
        elif kind == "buttons":
            _, buttons, header, body, footer = item
            print(f"\n  Bot msg: {header or ''} {body}".strip())
            if footer:
                print(f"           ({footer})")
            for b in buttons:
                print(f"           >>> [ {b['title']} ]  ->  type: {b['id']}")
                last_turn_buttons.append((b["id"], b["title"]))
        elif kind == "media":
            print(f"\n  Bot sends {item[1]}: {item[2]}")
            if item[3]:
                print(f"           ({item[3]})")
        elif kind == "list":
            print(f"\n  Bot menu: {item[1]}")
        elif kind.startswith("weird"):
            pass
    outbox.clear()


def send_message(wa_id, payload):
    outbox.clear()
    response = client.post("/webhook", json=payload)
    if response.status_code != 200:
        print(f"  !!! webhook returned {response.status_code}: {response.text}")
    print_bot_turn()


def send_text(wa_id, body):
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": wa_id,
                        "id": "local-msg",
                        "type": "text",
                        "text": {"body": body},
                    }]
                }
            }]
        }]
    }
    send_message(wa_id, payload)


def send_button(wa_id, button_id):
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": wa_id,
                        "id": "local-msg",
                        "type": "interactive",
                        "interactive": {
                            "type": "button_reply",
                            "button_reply": {"id": button_id, "title": button_id},
                        },
                    }]
                }
            }]
        }]
    }
    send_message(wa_id, payload)


def resolve_button(text):
    lowered = text.strip().lower()
    for button_id, title in last_turn_buttons:
        if lowered == button_id.lower() or lowered == title.lower():
            return button_id
        if lowered in title.lower():
            return button_id
    return None


def main():
    print("=" * 64)
    print(" WhatsApp Learning Bot - local playground")
    print(" Type 'hi' to start the conversation.")
    print(" When the bot offers buttons, just type the button label.")
    print(" Try: 'enroll', 'ask_ai_tutor', 'ai_assess', 'continue', 'A', 'B', 'C'")
    print(" Free text (any question) -> AI Tutor.  'exit' leaves Tutor mode.")
    print(" Type 'q' to quit the playground.")
    print("=" * 64)

    patches = [
        patch("bot.whatsapp.send_text", fake_send_text),
        patch("bot.whatsapp.send_buttons", fake_send_buttons),
        patch("bot.whatsapp.send_media", fake_send_media),
        patch("bot.whatsapp.send_list", fake_send_list),
        patch("bot.whatsapp.mark_as_read", fake_mark_read),
        patch("bot.ai_tutor.answer_question", fake_tutor),
    ]
    for p in patches:
        p.start()
    try:
        while True:
            try:
                raw = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                return

            if raw.lower() in ("q", "quit", ":q"):
                print("Bye!")
                return

            if not raw:
                continue

            button_id = resolve_button(raw)
            if button_id:
                print(f"  -> tapped button [{button_id}]")
                send_button(FAKE_USER, button_id)
            else:
                send_text(FAKE_USER, raw)
    finally:
        for p in patches:
            p.stop()


if __name__ == "__main__":
    main()