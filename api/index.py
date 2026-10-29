"""
api/index.py

FastAPI entry point for the WhatsApp Learning Bot (works locally and deployed
on Vercel as a Python serverless function).

Routes
------
GET  /webhook, /api/webhook   - Meta webhook verification (hub.mode / verify_token / challenge)
POST /webhook, /api/webhook   - Meta webhook events (all incoming user messages)
GET  /admin, /dashboard       - Admin & Analytics Dashboard
GET  /, /health               - Health check
"""

import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from bot import ai_tutor, db, state, whatsapp
from content import curriculum

# --- Logging (visible in Vercel Logs) ----------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

# --- Initialize DB on startup ---
try:
    db.init_db()
except Exception as e:
    logger.warning(f"DB init warning: {e}")

# --- Config ------------------------------------------------------------------
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "local-test")

# --- Button ids --------------------------------------------------------------
ENROLL = "enroll"
RESUME = "resume_course"
RESTART = "restart_course"
ASK_TUTOR = "ask_ai_tutor"
ASSESS = "ai_assess"
READY_QUIZ = "quiz_ready"
EXIT_TUTOR = "exit_tutor"
TUTOR_RESUME = "tutor_resume"
ANSWER_PREFIX = "ans:"
ASSESS_PREFIX = "assess:"

GREETINGS = {"hi", "hello", "hey", "start", "help"}
MODE_ABORT = {"exit", "quit", "back"}
LESSON_GO = {"ready", "continue", "next", "quiz", "go", "resume"}

app = FastAPI(title="EdTech Hub Learning Bot")

# --- Admin dashboard routes ---------------------------------------------------
try:
    from api.admin import router as admin_router, admin_dashboard
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

    @app.get("/dashboard", response_class=HTMLResponse)
    @app.get("/dashboard/", response_class=HTMLResponse)
    @app.get("/api/dashboard", response_class=HTMLResponse)
    async def dashboard_view(request: Request):
        return await admin_dashboard(request)
except Exception as e:
    logger.error(f"Failed to load admin router: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------
@app.get("/")
@app.get("/health")
@app.get("/api")
async def health_check(request: Request):
    # Check if Meta sent verification request to root
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified at root (%s)", mode)
        return Response(content=challenge, media_type="text/plain")

    return {
        "status": "ok",
        "message": "EdTech Hub WhatsApp Learning Bot is running",
        "admin_dashboard": "/admin",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# GET: webhook verification
# ---------------------------------------------------------------------------
@app.get("/webhook")
@app.get("/api/webhook")
async def webhook_verification(request: Request):
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
        content='{"status": "ok", "message": "WhatsApp webhook endpoint"}',
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# POST: webhook events
# ---------------------------------------------------------------------------
@app.post("/webhook")
@app.post("/api/webhook")
@app.post("/api")
async def handle_post(request: Request):
    try:
        data = await request.json()
        logger.debug("Incoming webhook payload: %s", data)

        for entry in data.get("entry", []):
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                for message in value.get("messages", []) or []:
                    # wa_id is the actual phone number of the user!
                    wa_id = message.get("from")
                    if wa_id:
                        await handle_incoming(str(wa_id), message)
    except Exception as exc:
        logger.error("Error handling webhook POST: %s", exc, exc_info=True)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Catch-all GET fallback for serverless rewrites
# ---------------------------------------------------------------------------
@app.get("/{path:path}")
async def catch_all_get(request: Request, path: str = ""):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")

    clean_path = path.strip("/").lower()
    if clean_path in ("admin", "dashboard"):
        from api.admin import admin_dashboard
        return await admin_dashboard(request)

    return Response(
        content='{"status": "ok", "message": "WhatsApp Learning Bot running"}',
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Incoming message router
# ---------------------------------------------------------------------------
async def handle_incoming(wa_id: str, message: dict) -> None:
    await whatsapp.mark_as_read(message.get("id"))
    msg_type = message.get("type")

    # Log user incoming interaction
    db.log_activity(wa_id, "incoming_message", f"Type: {msg_type}")

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
# Text command router (phase-aware & resume-aware)
# ---------------------------------------------------------------------------
async def handle_text(wa_id: str, raw: str) -> None:
    text = raw.strip()
    low = text.lower()
    cur = state.get_state(wa_id)
    phase = cur.get("phase")

    # greetings -> intro or resume menu
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

    # lesson or resume shortcuts
    if low in LESSON_GO:
        if phase == "quiz":
            await send_quiz(wa_id)
            return
        elif phase == "lesson":
            await send_quiz(wa_id)
            return
        else:
            # User was idle or stepped away, resume where they left off!
            lesson = state.current_lesson(cur)
            if lesson:
                await deliver_lesson(wa_id, lesson)
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
    db.log_activity(wa_id, "button_click", button_id)

    if button_id in (ENROLL, RESUME):
        cur = state.get_state(wa_id)
        # Check if user already has course progress - resume without losing state!
        lesson_idx = cur.get("lesson_index", 0)
        completed = cur.get("completed_lessons") or []

        if (lesson_idx > 0 or len(completed) > 0) and cur.get("phase") != "complete":
            # Resume existing course
            state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID, restart=False)
            lesson = state.current_lesson(state.get_state(wa_id))
            if cur.get("phase") == "quiz":
                await send_quiz(wa_id)
            else:
                await deliver_lesson(wa_id, lesson)
            return

        # Start fresh
        state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID, restart=False)
        lesson = state.current_lesson(state.get_state(wa_id))
        await deliver_lesson(wa_id, lesson)
        return

    if button_id == RESTART:
        state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID, restart=True)
        await whatsapp.send_text(wa_id, "Course reset! Starting Module 1:")
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
# Menu / intro (Resume-Aware!)
# ---------------------------------------------------------------------------
async def send_menu(wa_id: str, fresh: bool = True) -> None:
    cur = state.get_state(wa_id)
    phase = cur.get("phase")
    lesson_idx = cur.get("lesson_index", 0)
    completed = cur.get("completed_lessons") or []

    # Check if user has existing progress in the course
    has_progress = (lesson_idx > 0 or len(completed) > 0) and phase != "complete"

    if fresh:
        if has_progress:
            lesson = state.current_lesson(cur)
            lesson_title = lesson["title"] if lesson else f"Module {lesson_idx + 1}"
            await whatsapp.send_text(
                wa_id,
                f"Welcome back to EdTech Hub!\n\n"
                f"You are currently on: {lesson_title} (Completed {len(completed)}/11 modules).\n\n"
                f"Choose an option below to continue where you left off:",
            )
        else:
            await whatsapp.send_text(wa_id, curriculum.BOT_INTRO)
            await whatsapp.send_media(
                wa_id,
                "video",
                curriculum.INTRO_VIDEO_URL,
                caption="EdTech Hub - AI for Educators",
            )
    else:
        await whatsapp.send_text(wa_id, "Main menu:")

    if has_progress:
        buttons = [
            {"id": RESUME, "title": "Resume Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": RESTART, "title": "Restart Course"},
        ]
    elif phase == "complete":
        buttons = [
            {"id": RESTART, "title": "Review / Restart"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": ASSESS, "title": "AI Self-Assessment"},
        ]
    else:
        buttons = [
            {"id": ENROLL, "title": "Enroll in Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": ASSESS, "title": "AI Self-Assessment"},
        ]

    await whatsapp.send_buttons(
        wa_id,
        "Choose an option:",
        buttons,
        header="EdTech Hub" if fresh else "Main Menu",
        footer="Tap an option",
    )


# ---------------------------------------------------------------------------
# Course delivery
# ---------------------------------------------------------------------------
async def deliver_lesson(wa_id: str, lesson) -> None:
    if lesson is None:
        await recover_or_start(wa_id)
        return

    db.log_activity(wa_id, "lesson_viewed", lesson.get("title", ""))

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
        await recover_or_start(wa_id)
        return

    quiz = curriculum.get_quiz(cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID, lesson["id"])
    if not quiz:
        await whatsapp.send_text(wa_id, "No quiz for this lesson. Moving forward:")
        outcome, next_lesson = state.advance_past_lesson(wa_id)
        if outcome == "lesson":
            await deliver_lesson(wa_id, next_lesson)
        else:
            await send_menu(wa_id, fresh=False)
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
        await recover_or_start(wa_id)
        return

    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson_id = lesson["id"]

    if not curriculum.is_valid_option(unit_id, lesson_id, answer):
        await whatsapp.send_text(wa_id, "Please tap A, B or C below.")
        await send_quiz(wa_id)
        return

    result = curriculum.check_answer(unit_id, lesson_id, answer)
    explanation = result["explanation"]

    # Record result in state and activity log
    state.record_quiz_result(wa_id, lesson_id, answer, result["correct"])

    if result["correct"]:
        await whatsapp.send_text(wa_id, f"Correct! {explanation} Moving on to the next module.")
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
        unit = curriculum.get_unit(unit_id)
        await whatsapp.send_text(wa_id, unit["complete_message"])
        await send_menu(wa_id, fresh=False)


# ---------------------------------------------------------------------------
# AI Tutor mode
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

    db.log_activity(wa_id, "tutor_query", question[:80])
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
    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
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
        l2 = state.current_lesson(state.get_state(wa_id))
        await deliver_lesson(wa_id, l2)
        return

    if resume == "quiz" and unit_id:
        await send_quiz(wa_id)
        return

    await send_menu(wa_id, fresh=False)


async def resume_from_tutor(wa_id: str) -> None:
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
            "Thank you for completing the AI Self-Assessment!\n\n"
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
    db.log_activity(wa_id, "free_text_ai", question[:80])
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
            "You already finished Unit 1! Type 'hi' to review lessons or ask anything.",
        )


# ---------------------------------------------------------------------------
# Graceful state recovery (database backed)
# ---------------------------------------------------------------------------
async def recover_or_start(wa_id: str) -> None:
    """Seamlessly load user progress from database without resetting."""
    cur = state.get_state(wa_id)
    if cur.get("phase") == "complete":
        await whatsapp.send_text(
            wa_id,
            "You have already completed the course! Type 'hi' to review or ask questions.",
        )
        await send_menu(wa_id, fresh=False)
        return

    # Check if there is a valid lesson
    lesson = state.current_lesson(cur)
    if lesson:
        await deliver_lesson(wa_id, lesson)
    else:
        # Start unit but do not wipe any quiz answers
        state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID, restart=False)
        l2 = state.current_lesson(state.get_state(wa_id))
        if l2:
            await deliver_lesson(wa_id, l2)
        else:
            await send_menu(wa_id, fresh=False)
