"""
api/index.py

FastAPI entry point for the WhatsApp Learning Bot (deployed on Vercel as a
Python serverless function).

Routes
------
GET  /webhook  - Meta webhook verification (hub.mode / verify_token / challenge)
POST /webhook  - Meta webhook events (all incoming user messages)
GET  /         - health check

User flows
----------
    'hi' / 'hello' / 'help'
        -> Welcome text + logo video + 3 buttons: Enroll / Ask AI Tutor / AI Self-Assessment

    Enroll in Course -> lesson text + media -> [Ask AI Tutor] [Continue]
        -> quiz A/B/C -> feedback -> next lesson or unit complete

    Ask AI Tutor (any phase)
        -> enters tutor mode (current-lesson context) with [Exit] [Continue]

    AI Self-Assessment (from menu)
        -> 4 short A/B/C questions collecting teacher's AI readiness -> back to menu

    Any other free text
        -> routed to Gemini AI Tutor with current-lesson context (if applicable)
        -> guided back to the active lesson / quiz / menu

    'exit' / 'quit' / 'back' (during tutor or assessment)
        -> returns to previous screen (lesson step, quiz, or menu)
"""

import logging
import os

from fastapi import FastAPI, Request, Response

from bot import ai_tutor, state, whatsapp
from content import curriculum

# --- Logging (visible in Vercel Logs) ----------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

# --- Config ------------------------------------------------------------------
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# --- Button ids --------------------------------------------------------------
ENROLL = "enroll"
ASK_TUTOR = "ask_ai_tutor"
ASSESS = "ai_assess"
READY_QUIZ = "quiz_ready"
EXIT_TUTOR = "exit_tutor"
TUTOR_RESUME = "tutor_resume"
ANSWER_PREFIX = "ans:"
ASSESS_PREFIX = "assess:"

GREETINGS = {"hi", "hello", "hey", "start", "help"}
MODE_ABORT = {"exit", "quit", "back"}
LESSON_GO = {"ready", "continue", "next", "quiz", "go"}

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
    except Exception as exc:
        logger.error("Error handling webhook POST: %s", exc, exc_info=True)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Incoming message router
# ---------------------------------------------------------------------------
async def handle_incoming(wa_id: str, message: dict) -> None:
    await whatsapp.mark_as_read(message.get("id"))
    msg_type = message.get("type")

    if msg_type == "text":
        await handle_text(wa_id, message.get("text", {}).get("body", "").strip())
        return

    if msg_type == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "button_reply":
            await handle_button_click(wa_id, interactive.get("button_reply", {}).get("id", ""))
        elif interactive.get("type") == "list_reply":
            await handle_button_click(wa_id, interactive.get("list_reply", {}).get("id", ""))
        return

    logger.info("Ignoring unsupported message type=%s from %s", msg_type, wa_id)
    await whatsapp.send_text(
        wa_id,
        "I can only read text messages. Type 'hi' to open the menu, "
        "or tap the buttons on screen.",
    )


# ---------------------------------------------------------------------------
# Text command router (phase-aware)
# ---------------------------------------------------------------------------
async def handle_text(wa_id: str, raw: str) -> None:
    text = raw.strip()
    low = text.lower()
    cur = state.get_state(wa_id)
    phase = cur.get("phase")

    # greetings -> full intro menu
    if low in GREETINGS:
        await send_menu(wa_id, fresh=True)
        return

    # 'menu' -> main menu (soft exit modes)
    if low == "menu":
        if phase == "tutor":
            state.exit_tutor(wa_id)
        elif phase == "assessment":
            state.abort_assessment(wa_id)
        await send_menu(wa_id, fresh=False)
        return

    # tutor mode: any remaining text = AI question
    if phase == "tutor":
        if low in MODE_ABORT:
            await exit_tutor_flow(wa_id)
            return
        await tutor_chat(wa_id, text)
        return

    # assessment mode: letters = answer, else prompt retry
    if phase == "assessment":
        if low in ("a", "b", "c"):
            await handle_assessment_answer(wa_id, low.upper())
            return
        idx = state.assessment_index(wa_id)
        await whatsapp.send_text(wa_id, "Please tap A, B or C below to answer.")
        await send_assessment_question(wa_id, idx)
        return

    # lesson phase: shortcut words -> continue to quiz
    if phase == "lesson" and low in LESSON_GO:
        await send_quiz(wa_id)
        return

    # quiz phase: letter typed -> answer
    if phase == "quiz" and low in ("a", "b", "c"):
        await handle_quiz_answer(wa_id, low.upper())
        return

    # everything else -> AI fallback (context-aware)
    await handle_ai_fallback(wa_id, text)


# ---------------------------------------------------------------------------
# Button routing
# ---------------------------------------------------------------------------
async def handle_button_click(wa_id: str, button_id: str) -> None:

    if button_id == ENROLL:
        state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID)
        lesson = state.current_lesson(state.get_state(wa_id))
        await deliver_lesson(wa_id, lesson)
        return

    if button_id == ASK_TUTOR:
        await enter_tutor_flow(wa_id)
        return

    if button_id == ASSESS:
        state.start_assessment(wa_id)
        await send_assessment_question(wa_id, 0)
        return

    if button_id == READY_QUIZ:
        await send_quiz(wa_id)
        return

    if button_id == EXIT_TUTOR:
        await exit_tutor_flow(wa_id)
        return

    if button_id == TUTOR_RESUME:
        await resume_from_tutor(wa_id)
        return

    if button_id.startswith(ASSESS_PREFIX):
        await handle_assessment_answer(wa_id, button_id[len(ASSESS_PREFIX):])
        return

    if button_id.startswith(ANSWER_PREFIX):
        await handle_quiz_answer(wa_id, button_id[len(ANSWER_PREFIX):])
        return

    logger.info("Unknown button id=%s from %s", button_id, wa_id)
    await send_menu(wa_id, fresh=False)


# ---------------------------------------------------------------------------
# Menu / intro
# ---------------------------------------------------------------------------
async def send_menu(wa_id: str, fresh: bool = True) -> None:
    if fresh:
        await whatsapp.send_text(wa_id, curriculum.BOT_INTRO)
        await whatsapp.send_media(
            wa_id,
            "video",
            curriculum.INTRO_VIDEO_URL,
            caption="EdTech Hub - AI for Educators",
        )
    else:
        await whatsapp.send_text(wa_id, "Back to the main menu:")

    await whatsapp.send_buttons(
        wa_id,
        "Choose an option:",
        [
            {"id": ENROLL, "title": "Enroll in Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": ASSESS, "title": "AI Self-Assessment"},
        ],
        header="EdTech Hub" if fresh else "Main Menu",
        footer="Tap an option",
    )


# ---------------------------------------------------------------------------
# Course delivery
# ---------------------------------------------------------------------------
async def deliver_lesson(wa_id: str, lesson) -> None:
    if lesson is None:
        await ask_restart(wa_id)
        return

    await whatsapp.send_text(wa_id, lesson["title"])
    for paragraph in lesson["body"]:
        await whatsapp.send_text(wa_id, paragraph)

    media = lesson.get("media")
    if media:
        await whatsapp.send_media(
            wa_id, media["type"], media["url"],
            caption=media.get("caption"), filename=media.get("filename"),
        )

    await whatsapp.send_buttons(
        wa_id,
        "Lesson complete - what would you like to do?",
        [
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": READY_QUIZ, "title": "Continue"},
        ],
        footer="Ask a question or continue to the quiz",
    )


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------
async def send_quiz(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    lesson = state.current_lesson(cur)

    if not lesson:
        await ask_restart(wa_id)
        return

    quiz = curriculum.get_quiz(cur["unit_id"], lesson["id"])
    if not quiz:
        await whatsapp.send_text(wa_id, "No quiz for this lesson yet.")
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
        footer="Tap A, B or C",
    )
    state.open_quiz(wa_id)


async def handle_quiz_answer(wa_id: str, answer: str) -> None:
    cur = state.get_state(wa_id)
    lesson = state.current_lesson(cur)

    if not lesson:
        await ask_restart(wa_id)
        return

    unit_id = cur["unit_id"]
    lesson_id = lesson["id"]

    if not curriculum.is_valid_option(unit_id, lesson_id, answer):
        await whatsapp.send_text(wa_id, "Please tap A, B or C below.")
        await send_quiz(wa_id)
        return

    result = curriculum.check_answer(unit_id, lesson_id, answer)
    explanation = result["explanation"]

    if result["correct"]:
        await whatsapp.send_text(wa_id, f"Correct! {explanation} Moving on to the next lesson.")
    else:
        await whatsapp.send_text(
            wa_id,
            f"Not quite - the correct answer was {result['correct_answer']}. "
            f"{explanation} Try again:",
        )
        await send_quiz(wa_id)
        return

    outcome, next_lesson = state.advance_past_lesson(wa_id)
    if outcome == "lesson":
        await deliver_lesson(wa_id, next_lesson)
    else:
        unit = curriculum.get_unit(cur["unit_id"])
        await whatsapp.send_text(wa_id, unit["complete_message"])
        await send_menu(wa_id, fresh=False)


# ---------------------------------------------------------------------------
# AI Tutor mode (in-course and full-conversation)
# ---------------------------------------------------------------------------
async def enter_tutor_flow(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    phase = cur.get("phase")

    lesson_id = None
    context_label = "the full course"
    if phase in ("lesson", "quiz"):
        lesson = state.current_lesson(cur)
        if lesson:
            lesson_id = lesson["id"]
            context_label = lesson["title"]

    state.enter_tutor(wa_id, lesson_id=lesson_id)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    if phase in ("lesson", "quiz") and cur.get("unit_id"):
        buttons.append({"id": TUTOR_RESUME, "title": "Continue Course"})

    await whatsapp.send_text(
        wa_id,
        f"AI Tutor mode - I have the course context ({context_label}). "
        "Ask me anything about the lesson! Type 'exit' or tap the button to leave.",
    )
    await whatsapp.send_buttons(
        wa_id, "What would you like to do?", buttons, footer="Tap an option",
    )


async def tutor_chat(wa_id: str, question: str) -> None:
    cur = state.get_state(wa_id)
    unit_id = cur.get("unit_id")
    lesson_id = cur.get("tutor_lesson")

    section = curriculum.lesson_as_context(unit_id, lesson_id) if unit_id and lesson_id else ""

    answer = await ai_tutor.answer_question(question, section=section)
    await whatsapp.send_text(wa_id, answer)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    if unit_id and cur.get("tutor_resume") in ("lesson", "quiz"):
        buttons.append({"id": TUTOR_RESUME, "title": "Continue Course"})

    await whatsapp.send_buttons(
        wa_id, "What next?", buttons, footer="Ask more or exit",
    )


async def exit_tutor_flow(wa_id: str) -> None:
    """Exit tutor and return to the previous screen."""
    cur = state.get_state(wa_id)
    unit_id = cur.get("unit_id")
    resume_lesson_id = cur.get("tutor_lesson")
    resume = state.exit_tutor(wa_id)

    if resume == "lesson" and unit_id:
        lesson = curriculum.get_lesson(unit_id, resume_lesson_id) if resume_lesson_id else None
        if lesson:
            await whatsapp.send_text(wa_id, f"Back to your lesson: {lesson['title']}")
            await whatsapp.send_buttons(
                wa_id, "What would you like to do?",
                [
                    {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                    {"id": READY_QUIZ, "title": "Continue"},
                ],
                footer="Ask a question or continue to the quiz",
            )
            return
        state.start_unit(wa_id, unit_id)
        l2 = state.current_lesson(state.get_state(wa_id))
        await deliver_lesson(wa_id, l2)
        return

    if resume == "quiz" and unit_id:
        await send_quiz(wa_id)
        return

    await send_menu(wa_id, fresh=False)


async def resume_from_tutor(wa_id: str) -> None:
    """Exit tutor and go back to lesson step buttons (Continue + Ask AI)."""
    await exit_tutor_flow(wa_id)


# ---------------------------------------------------------------------------
# Self-Assessment
# ---------------------------------------------------------------------------
async def send_assessment_question(wa_id: str, index: int) -> None:
    question = curriculum.get_assessment_question(index)
    if not question:
        await send_menu(wa_id, fresh=False)
        return

    total = len(curriculum.ASSESSMENT)
    options = question["options"]
    body = f"{question['question']}"
    for letter in ("A", "B", "C"):
        if letter in options:
            body += f"\n\n{letter}) {options[letter]}"

    await whatsapp.send_buttons(
        wa_id,
        body,
        [{"id": f"{ASSESS_PREFIX}{letter}", "title": letter} for letter in options],
        header=f"AI Self-Assessment ({index + 1}/{total})",
        footer="Tap A, B or C",
    )


async def handle_assessment_answer(wa_id: str, letter: str) -> None:
    cur = state.get_state(wa_id)
    idx = cur.get("assessment_index", 0)
    question = curriculum.get_assessment_question(idx)

    if not question or letter not in question.get("options", {}):
        await whatsapp.send_text(wa_id, "That isn't a valid option. Tap A, B or C below.")
        await send_assessment_question(wa_id, idx)
        return

    result = state.record_assessment_answer(wa_id, question["id"], letter)
    logger.info("Assessment answer: %s = %s from %s", question["id"], letter, wa_id)

    if result["done"]:
        await whatsapp.send_text(
            wa_id,
            "Thank you for completing the AI Self-Assessment! "
            "Based on your answers, the AI for Educators course is a great place to start. "
            "Ready to begin?",
        )
        await send_menu(wa_id, fresh=False)
    else:
        next_idx = state.assessment_index(wa_id)
        await send_assessment_question(wa_id, next_idx)


# ---------------------------------------------------------------------------
# AI fallback for free text (context-aware)
# ---------------------------------------------------------------------------
async def handle_ai_fallback(wa_id: str, question: str) -> None:
    cur = state.get_state(wa_id)
    phase = cur.get("phase")
    unit_id = cur.get("unit_id")
    lesson = state.current_lesson(cur) if phase in ("lesson", "quiz") else None

    section = ""
    if phase == "lesson" and lesson:
        section = curriculum.lesson_as_context(unit_id, lesson["id"])
    elif phase == "quiz" and lesson:
        section = curriculum.quiz_as_context(unit_id, lesson["id"])

    logger.info("AI fallback (%s) phase=%s: %s", wa_id, phase, question[:120])
    answer = await ai_tutor.answer_question(question, section=section)
    await whatsapp.send_text(wa_id, answer)

    if phase == "lesson" and lesson:
        await whatsapp.send_buttons(
            wa_id, "What would you like to do?",
            [
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                {"id": READY_QUIZ, "title": "Continue"},
            ],
            footer="Ask a question or continue to the quiz",
        )
    elif phase == "quiz" and lesson:
        await send_quiz(wa_id)
    elif phase == "complete":
        await whatsapp.send_text(
            wa_id,
            "You already finished Unit 1! Type 'hi' to restart or ask anything.",
        )


# ---------------------------------------------------------------------------
# Restart helper (cold-start / lost state)
# ---------------------------------------------------------------------------
async def ask_restart(wa_id: str) -> None:
    await whatsapp.send_text(
        wa_id,
        "It looks like your progress was reset (this server doesn't have "
        "a database yet). Tap below to start the course again.",
    )
    await whatsapp.send_buttons(
        wa_id, "Start the AI for Educators course?",
        [
            {"id": ENROLL, "title": "Enroll in Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
        ],
        footer="Tap to start",
    )