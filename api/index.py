"""
api/index.py

FastAPI entry point for the WhatsApp Learning Bot (deployed on Vercel as a
Python serverless function).

Routes
------
GET  /webhook  - Meta webhook verification (hub.mode / verify_token / challenge)
POST /webhook  - Meta webhook events (all incoming user messages)
GET  /         - health check

Flow
----
    "hi" -> welcome + interactive buttons [Start Unit 1] [Ask AI Tutor]
    Start Unit 1 -> stream lesson text + media -> "Ready for Quiz?" button
    Ready for Quiz -> quiz question with A/B/C buttons
    correct answer -> feedback + next lesson (or unit complete)
    wrong answer   -> feedback with the right option + retry the same quiz
    any other free text -> routed to the AI Tutor (Gemini), then guided back
                           to the active lesson/quiz
"""

import logging
import os

from fastapi import FastAPI, Request, Response

from bot import ai_tutor, state, whatsapp
from content import curriculum

# --- Logging (visible in Vercel Logs) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

# --- Config ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# --- Button / option ids ---
START_UNIT = "start_unit_1"
ASK_TUTOR = "ask_ai_tutor"
READY_QUIZ = "quiz_ready"
ANSWER_PREFIX = "ans:"  # answer button ids look like "ans:A", "ans:B", "ans:C"
GREETINGS = {"hi", "hello", "hey", "start", "menu", "help"}

app = FastAPI()


# ---------------------------------------------------------------------------
# GET: webhook verification + health check
# ---------------------------------------------------------------------------
@app.get("/{path:path}")
async def handle_get(request: Request, path: str = ""):
    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified (%s)", mode)
        return Response(content=challenge, media_type="text/plain")

    if token != VERIFY_TOKEN and mode:
        logger.warning("Webhook verification failed: bad verify_token")
        return Response(content="Forbidden", media_type="text/plain", status_code=403)

    return Response(
        content='{"status": "ok", "message": "WhatsApp Learning Bot running"}',
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# POST: webhook events
# ---------------------------------------------------------------------------
@app.post("/{path:path}")
async def handle_post(request: Request, path: str = ""):
    try:
        data = await request.json()
        logger.debug("Incoming webhook payload: %s", data)

        for entry in data.get("entry", []):
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                for message in value.get("messages", []) or []:
                    wa_id = message.get("from")
                    if wa_id:
                        await handle_incoming(wa_id, message)
    except Exception as exc:  # noqa: BLE001 - never crash out of the webhook
        logger.error("Error handling webhook POST: %s", exc, exc_info=True)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Incoming message router
# ---------------------------------------------------------------------------
async def handle_incoming(wa_id: str, message: dict) -> None:
    await whatsapp.mark_as_read(message.get("id"))

    msg_type = message.get("type")

    if msg_type == "text":
        raw = message.get("text", {}).get("body", "").strip()
        lowered = raw.lower()

        if lowered in GREETINGS:
            await send_menu(wa_id)
            return

        await handle_ai_fallback(wa_id, raw)
        return

    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            button_id = interactive.get("button_reply", {}).get("id", "")
            await handle_button_click(wa_id, button_id)
        elif interactive.get("type") == "list_reply":
            list_id = interactive.get("list_reply", {}).get("id", "")
            await handle_button_click(wa_id, list_id)
        return

    logger.info("Ignoring unsupported message type=%s from %s", msg_type, wa_id)
    await whatsapp.send_text(
        wa_id,
        "I can only read text messages. Type 'hi' to open the menu, "
        "or type a question about your course.",
    )


# ---------------------------------------------------------------------------
# Onboarding / menu
# ---------------------------------------------------------------------------
async def send_menu(wa_id: str) -> None:
    welcome = (
        "Welcome to the EdTech Learning Bot! "
        "I will guide you through Unit 1: Digital Literacy for Teachers, "
        "step by step, with quizzes along the way. "
        "Choose an option below to begin."
    )
    await whatsapp.send_buttons(
        wa_id,
        welcome,
        [
            {"id": START_UNIT, "title": "Start Unit 1"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
        ],
        header="EdTech Learning Bot",
        footer="Tap an option below",
    )


# ---------------------------------------------------------------------------
# Interactive button routing
# ---------------------------------------------------------------------------
async def handle_button_click(wa_id: str, button_id: str) -> None:
    if button_id == START_UNIT:
        state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID)
        lesson = state.current_lesson(state.get_state(wa_id))
        await deliver_lesson(wa_id, lesson)
        return

    if button_id == ASK_TUTOR:
        await whatsapp.send_text(
            wa_id,
            "Go ahead - ask me anything about Unit 1 "
            "(digital literacy, using devices, evaluating resources). "
            "Type your question now.",
        )
        return

    if button_id == READY_QUIZ:
        await send_quiz(wa_id)
        return

    if button_id.startswith(ANSWER_PREFIX):
        await handle_quiz_answer(wa_id, button_id[len(ANSWER_PREFIX):])
        return

    logger.info("Unknown button id=%s from %s", button_id, wa_id)
    await send_menu(wa_id)


# ---------------------------------------------------------------------------
# Course delivery
# ---------------------------------------------------------------------------
async def deliver_lesson(wa_id: str, lesson) -> None:
    await whatsapp.send_text(wa_id, f"{lesson['title']}")

    for paragraph in lesson["body"]:
        await whatsapp.send_text(wa_id, paragraph)

    media = lesson.get("media")
    if media:
        await whatsapp.send_media(
            wa_id,
            media["type"],
            media["url"],
            caption=media.get("caption"),
            filename=media.get("filename"),
        )

    await whatsapp.send_buttons(
        wa_id,
        "Lesson complete! Ready for the quiz on this topic?",
        [{"id": READY_QUIZ, "title": "Ready for Quiz"}],
        footer="Tap to take the quiz",
    )


async def send_quiz(wa_id: str) -> None:
    cur_state = state.get_state(wa_id)
    lesson = state.current_lesson(cur_state)

    if not lesson:
        logger.info("Quiz requested but no active lesson for %s", wa_id)
        await send_menu(wa_id)
        return

    quiz = curriculum.get_quiz(cur_state["unit_id"], lesson["id"])
    if not quiz:
        logger.error("Missing quiz for unit=%s lesson=%s", cur_state["unit_id"], lesson["id"])
        await whatsapp.send_text(wa_id, "There is no quiz for this lesson yet.")
        return

    options = quiz["options"]
    body = quiz["question"]
    for letter in ("A", "B", "C", "D", "E"):
        if letter in options:
            body += f"\n\n{letter}) {options[letter]}"

    await whatsapp.send_buttons(
        wa_id,
        body,
        [{"id": f"{ANSWER_PREFIX}{letter}", "title": letter} for letter in options],
        header=f"Quiz - {lesson['title']}",
        footer="Reply A, B or C via the buttons",
    )
    state.open_quiz(wa_id)


async def handle_quiz_answer(wa_id: str, answer: str) -> None:
    cur_state = state.get_state(wa_id)
    lesson = state.current_lesson(cur_state)

    if not lesson:
        logger.info("Quiz answer %s but no active quiz for %s", answer, wa_id)
        await send_menu(wa_id)
        return

    unit_id = cur_state["unit_id"]
    lesson_id = lesson["id"]

    if not curriculum.is_valid_option(unit_id, lesson_id, answer):
        await whatsapp.send_text(
            wa_id, "That is not one of the options. Please tap A, B or C below."
        )
        await send_quiz(wa_id)
        return

    result = curriculum.check_answer(unit_id, lesson_id, answer)
    explanation = result["explanation"]

    if result["correct"]:
        await whatsapp.send_text(
            wa_id, f"Correct! {explanation} Moving on to the next lesson."
        )
    else:
        await whatsapp.send_text(
            wa_id,
            f"Not quite - the correct answer was {result['correct_answer']}. "
            f"{explanation} Try this one again:",
        )
        await send_quiz(wa_id)
        return

    outcome, next_lesson = state.advance_past_lesson(wa_id)
    if outcome == "lesson":
        await deliver_lesson(wa_id, next_lesson)
    else:
        unit_meta = curriculum.get_unit(unit_id)
        await whatsapp.send_text(wa_id, unit_meta["complete_message"])
        await send_menu(wa_id)


# ---------------------------------------------------------------------------
# AI fallback for free text
# ---------------------------------------------------------------------------
async def handle_ai_fallback(wa_id: str, question: str) -> None:
    logger.info("AI fallback (%s): %s", wa_id, question[:160])
    answer = await ai_tutor.answer_question(question)
    await whatsapp.send_text(wa_id, answer)

    cur_state = state.get_state(wa_id)

    if cur_state.get("phase") == "lesson":
        await whatsapp.send_buttons(
            wa_id,
            "Back to your lesson - tap below when you are ready.",
            [{"id": READY_QUIZ, "title": "Ready for Quiz"}],
        )
    elif cur_state.get("phase") == "quiz":
        await send_quiz(wa_id)
    elif cur_state.get("phase") == "complete":
        await whatsapp.send_text(
            wa_id,
            "You already finished Unit 1! Type 'hi' to start again or ask anything.",
        )