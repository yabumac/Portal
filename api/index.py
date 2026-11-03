"""
api/index.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import traceback

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

app = FastAPI(title="EdTech Hub Learning Bot")

# --- Logging (visible in Vercel Logs) ----------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

_STARTUP_ERROR = None
try:
    from bot import ai_tutor, db, state, whatsapp
    from content import curriculum
    try:
        db.init_db()
    except Exception as e:
        logger.warning(f"DB init warning: {e}")
except Exception as e:
    _STARTUP_ERROR = f"Startup error: {e}\n{traceback.format_exc()}"
    logger.error("Startup error: %s", _STARTUP_ERROR)

@app.middleware("http")
async def startup_error_catcher(request: Request, call_next):
    if _STARTUP_ERROR:
        return JSONResponse(
            status_code=500,
            content={"status": "startup_failed", "error": _STARTUP_ERROR}
        )
    try:
        return await call_next(request)
    except Exception as req_err:
        logger.error("Unhandled request exception: %s", req_err, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "request_failed", "error": str(req_err), "trace": traceback.format_exc()}
        )

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

# --- Admin dashboard routes ---------------------------------------------------
try:
    from api.admin import router as admin_router, admin_dashboard
    app.include_router(admin_router, prefix="/admin", tags=["admin"])
    app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

    @app.get("/admin", response_class=HTMLResponse)
    @app.get("/admin/", response_class=HTMLResponse)
    @app.get("/api/admin", response_class=HTMLResponse)
    @app.get("/api/admin/", response_class=HTMLResponse)
    @app.get("/dashboard", response_class=HTMLResponse)
    @app.get("/dashboard/", response_class=HTMLResponse)
    @app.get("/api/dashboard", response_class=HTMLResponse)
    async def dashboard_view(request: Request):
        return await admin_dashboard(request)

    @app.get("/media/logo.png")
    @app.get("/logo.png")
    @app.get("/static/logo.png")
    async def serve_company_logo():
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for candidate in (
            os.path.join(base, "public", "logo.png"),
            os.path.join(base, "media", "logo.png"),
            os.path.join(base, "public", "media", "logo.png"),
        ):
            if os.path.exists(candidate):
                return FileResponse(candidate, media_type="image/png")
        return Response(status_code=404)

    @app.get("/media/{filename:path}")
    async def serve_media_asset(filename: str):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for candidate in (
            os.path.join(base, "public", "media", filename),
            os.path.join(base, "public", filename),
            os.path.join(base, "media", filename),
        ):
            if os.path.exists(candidate):
                media_type = "video/mp4" if filename.lower().endswith(".mp4") else ("image/png" if filename.lower().endswith(".png") else "application/octet-stream")
                return FileResponse(candidate, media_type=media_type)
        return Response(status_code=404)
except Exception as e:
    logger.error(f"Failed to load admin router: {e}", exc_info=True)


CANONICAL_DOMAIN = "portal-six-sepia-65.vercel.app"


def get_public_media_url(filename_or_path: str) -> str:
    """Build a fully qualified public HTTPS URL for media delivery to WhatsApp."""
    clean = filename_or_path.lstrip("./").lstrip("/")
    if not clean.startswith("media/"):
        clean = f"media/{clean}"
    # Prioritize CANONICAL_DOMAIN or explicit PUBLIC_URL so Meta never requests ephemeral preview domains
    host = os.getenv("PUBLIC_URL") or CANONICAL_DOMAIN
    if not host.startswith(("http://", "https://")):
        host = f"https://{host}"
    return f"{host.rstrip('/')}/{clean}"


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

    # If Vercel rewrote an admin or dashboard request to /api
    raw_path = (
        request.headers.get("x-matched-path")
        or request.headers.get("x-invoke-path")
        or request.headers.get("x-forwarded-uri")
        or ""
    ).lower()

    if "admin/login" in raw_path or raw_path.endswith("/login"):
        from api.admin import login_page
        return await login_page()

    if "admin/api/analytics" in raw_path or "api/analytics" in raw_path:
        from api.admin import get_analytics_json
        return await get_analytics_json(request)

    if "admin" in raw_path or "dashboard" in raw_path or params.get("password") or params.get("pass"):
        from api.admin import admin_dashboard
        return await admin_dashboard(request)

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
@app.get("/webhook/")
@app.get("/api/webhook")
@app.get("/api/webhook/")
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
# POST: webhook events (all paths caught for serverless compatibility)
# ---------------------------------------------------------------------------
@app.post("/")
@app.post("/webhook")
@app.post("/webhook/")
@app.post("/api")
@app.post("/api/")
@app.post("/api/webhook")
@app.post("/api/webhook/")
@app.post("/api/index.py")
@app.post("/{path:path}")
async def handle_post(request: Request, path: str = ""):
    clean_path = path.strip("/").lower()

    # Route admin login POST
    if clean_path.startswith("admin/login") or clean_path == "login":
        from api.admin import login_submit
        return await login_submit(request)

    try:
        data = await request.json()
        logger.info("Incoming webhook payload received: %s", str(data)[:400])

        for entry in data.get("entry", []):
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                for message in value.get("messages", []) or []:
                    # wa_id is the actual phone number of the user!
                    wa_id = message.get("from")
                    if wa_id:
                        logger.info("Processing message from wa_id=%s, type=%s", wa_id, message.get("type"))
                        await handle_incoming(str(wa_id), message)
    except Exception as exc:
        logger.error("Error handling webhook POST: %s", exc, exc_info=True)
        try:
            db.log_activity("system", "webhook_post_error", str(exc))
        except Exception:
            pass

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
    if clean_path.startswith("admin/login") or clean_path == "login":
        from api.admin import login_page
        return await login_page()

    if clean_path in ("admin/api/analytics", "api/admin/analytics", "api/analytics"):
        from api.admin import get_analytics_json
        return await get_analytics_json(request)

    if clean_path in ("admin/export/csv", "export/csv"):
        from api.admin import export_users_csv
        return await export_users_csv(request)

    if clean_path in ("admin", "dashboard", "admin/dashboard", "api/admin", "api/dashboard") or clean_path.startswith("admin/") or params.get("password") or params.get("pass"):
        from api.admin import admin_dashboard
        return await admin_dashboard(request)

    if clean_path in ("media/logo.png", "logo.png", "static/logo.png"):
        from api.admin import admin_logo
        return await admin_logo()

    if clean_path.startswith("media/"):
        filename = clean_path[len("media/"):].strip("/")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for candidate in (
            os.path.join(base, "public", "media", filename),
            os.path.join(base, "public", filename),
            os.path.join(base, "media", filename),
        ):
            if os.path.exists(candidate):
                media_type = "video/mp4" if filename.endswith(".mp4") else ("image/png" if filename.endswith(".png") else "application/octet-stream")
                return FileResponse(candidate, media_type=media_type)

    return Response(
        content='{"status": "ok", "message": "WhatsApp Learning Bot running"}',
        media_type="application/json",
    )


# ---------------------------------------------------------------------------
# Incoming message router
# ---------------------------------------------------------------------------
async def handle_incoming(wa_id: str, message: dict) -> None:
    try:
        msg_id = message.get("id")
        if msg_id:
            await whatsapp.mark_as_read(msg_id)
    except Exception as read_err:
        logger.warning("Could not mark message as read (non-fatal): %s", read_err)

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

    # Replay or send video on demand
    if low in ("video", "watch video", "watch", "play video", "clip", "replay", "show video", "send video"):
        lesson = state.current_lesson(cur)
        if lesson and lesson.get("video_file"):
            v_url = get_public_media_url(lesson["video_file"])
            caption = f"{lesson['title']}\n\n{lesson.get('caption') or 'Watch the lesson video above:'}"
            await whatsapp.send_media(wa_id, "video", v_url, caption=caption)
        else:
            await whatsapp.send_text(wa_id, "Please tap 'Enroll in Course' to view the first module video.")
        return

    # Direct enrollment or start commands
    if low in ("enroll", "start", "begin", "learn", "study", "join", "course"):
        await handle_button_click(wa_id, ENROLL)
        return

    # Direct module jumping (e.g. "module 1", "module 2")
    for mod_num in range(1, 8):
        if low in (f"module {mod_num}", f"mod {mod_num}", f"lesson {mod_num}"):
            unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
            state.start_unit(wa_id, unit_id, restart=False)
            updated = state.get_state(wa_id)
            updated["lesson_index"] = mod_num - 1
            updated["phase"] = "lesson"
            state.set_state(wa_id, updated)
            lesson = state.current_lesson(updated)
            if lesson:
                await deliver_lesson(wa_id, lesson)
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

    # quiz phase: letter or option number typed -> answer
    if phase == "quiz" and low in ("a", "b", "c", "d", "1", "2", "3", "4"):
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
        lesson_idx = cur.get("lesson_index", 0)
        completed = cur.get("completed_lessons") or []

        # Check if user already has course progress - resume without losing state!
        has_progress = (
            cur.get("phase") in ("lesson", "quiz", "tutor", "assessment")
            or (lesson_idx is not None and lesson_idx > 0)
            or len(completed) > 0
        ) and cur.get("phase") != "complete"

        if has_progress:
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
        await whatsapp.send_text(wa_id, "Course reset. Starting Module 1:")
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

    if button_id == "watch_video":
        cur = state.get_state(wa_id)
        lesson = state.current_lesson(cur)
        if lesson and lesson.get("video_file"):
            v_url = get_public_media_url(lesson["video_file"])
            caption = f"{lesson['title']}\n\n{lesson.get('caption') or 'Watch the lesson video above:'}"
            await whatsapp.send_media(wa_id, "video", v_url, caption=caption)
        else:
            await whatsapp.send_text(wa_id, "No video clip found for this section.")
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

    # Check if user has active or existing progress in the course
    has_progress = (
        phase in ("lesson", "quiz", "tutor", "assessment")
        or (lesson_idx is not None and lesson_idx > 0)
        or len(completed) > 0
    ) and phase != "complete"

    if fresh:
        if has_progress:
            lesson = state.current_lesson(cur)
            lesson_title = lesson["title"] if lesson else f"Module {(lesson_idx or 0) + 1}"
            total_mods = curriculum.total_lessons(cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID) or 7
            await whatsapp.send_text(
                wa_id,
                f"Welcome back to EdTech Hub.\n\n"
                f"You are currently on: {lesson_title} (Completed {len(completed)}/{total_mods} modules).\n\n"
                f"Choose an option below to continue where you left off:",
            )
        else:
            # Send company logo image upon greeting
            try:
                logo_url = get_public_media_url("logo.png")
                await whatsapp.send_media(
                    wa_id,
                    "image",
                    logo_url,
                    caption="EdTech Hub - AI for Ethiopian Educators",
                )
                await asyncio.sleep(0.5)
            except Exception as logo_err:
                logger.warning("Could not send welcome logo (non-blocking): %s", logo_err)

            # Send welcome overview video clip
            try:
                video_url = get_public_media_url("vid_01_welcome.mp4")
                await whatsapp.send_media(
                    wa_id,
                    "video",
                    video_url,
                    caption="Course Overview: 4 Learning Objectives",
                )
                await asyncio.sleep(0.6)
            except Exception as media_err:
                logger.warning("Could not send intro video (non-blocking): %s", media_err)

            await whatsapp.send_text(wa_id, curriculum.BOT_INTRO)
            await asyncio.sleep(0.3)
    else:
        await whatsapp.send_text(wa_id, "Main menu:")

    if has_progress:
        buttons = [
            {"id": RESUME, "title": "Continue Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": RESTART, "title": "Restart Course"},
        ]
    elif phase == "complete":
        buttons = [
            {"id": RESTART, "title": "Review / Restart"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": ASSESS, "title": "Take Survey"},
        ]
    else:
        buttons = [
            {"id": ENROLL, "title": "Enroll in Course"},
            {"id": ASSESS, "title": "Take Survey"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
        ]

    await whatsapp.send_buttons(
        wa_id,
        "Choose an option:",
        buttons,
        header="EdTech Hub" if fresh else "Main Menu",
        footer="Tap an option",
    )


# ---------------------------------------------------------------------------
# Course delivery (Video & Picture-First Methodology)
# ---------------------------------------------------------------------------
async def deliver_lesson(wa_id: str, lesson) -> None:
    if lesson is None:
        await recover_or_start(wa_id)
        return

    db.log_activity(wa_id, "lesson_viewed", lesson.get("title", ""))

    # 1. Chopped video clip first (Primary learning medium)
    video_file = lesson.get("video_file")
    if video_file:
        try:
            v_url = get_public_media_url(video_file)
            caption = f"{lesson['title']}\n\n{lesson.get('caption') or 'Watch the lesson video above:'}"
            await whatsapp.send_media(
                wa_id,
                "video",
                v_url,
                caption=caption,
            )
            await asyncio.sleep(0.6)
        except Exception as vid_err:
            logger.warning("Could not send lesson video clip: %s", vid_err)
    else:
        # Title text if no video clip
        await whatsapp.send_text(wa_id, lesson["title"])
        await asyncio.sleep(0.4)

    # 2. Visual diagram / slide frame
    image_file = lesson.get("image_file")
    if image_file:
        try:
            img_url = get_public_media_url(image_file)
            await whatsapp.send_media(
                wa_id,
                "image",
                img_url,
                caption=f"Visual Guide: {lesson['title']}",
            )
            await asyncio.sleep(0.5)
        except Exception as img_err:
            logger.warning("Could not send lesson image: %s", img_err)

    # 3. Concise instructional summary points
    for paragraph in lesson.get("body", []):
        await whatsapp.send_text(wa_id, paragraph)
        await asyncio.sleep(0.3)

    # 4. Next step buttons
    # 4. Next step buttons
    await whatsapp.send_buttons(
        wa_id,
        "Module complete - choose an option below:",
        [
            {"id": READY_QUIZ, "title": "Continue to Quiz"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
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
    for key in options:
        body += f"\n\n{key}) {options[key]}"

    await whatsapp.send_buttons(
        wa_id,
        body,
        [{"id": f"{ANSWER_PREFIX}{key}", "title": key} for key in options],
        header=f"Quiz - {lesson['title']}",
        footer="Tap an option",
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
        quiz = curriculum.get_quiz(unit_id, lesson_id)
        opts_hint = ", ".join(quiz["options"].keys()) if quiz else "your choice"
        await whatsapp.send_text(wa_id, f"Please tap {opts_hint} below.")
        await send_quiz(wa_id)
        return

    result = curriculum.check_answer(unit_id, lesson_id, answer)
    explanation = result["explanation"]

    # Record result in state and activity log
    state.record_quiz_result(wa_id, lesson_id, answer, result["correct"])

    if result["correct"]:
        await whatsapp.send_text(wa_id, f"Correct! {explanation} Moving on to the next module.")
    else:
        hint_msg = result.get("hint") or "Review the lesson materials and key principles, then try again."
        await whatsapp.send_text(
            wa_id,
            f"Not quite. Here is a helpful hint:\n\n{hint_msg}\n\nPlease try again below:",
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
    lesson = state.current_lesson(cur)
    lesson_id = lesson["id"] if lesson else None
    context_label = lesson["title"] if lesson else "Module 1: AI Basics and The Teacher as Editor"

    state.enter_tutor(wa_id, lesson_id=lesson_id)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    if cur.get("unit_id") or cur.get("tutor_resume"):
        buttons.append({"id": TUTOR_RESUME, "title": "Continue Course"})

    await whatsapp.send_text(
        wa_id,
        f"AI Tutor active for: {context_label}\n\n"
        "Ask any question about this module or classroom AI strategy! "
        "Type your question below, or tap an option:",
    )
    await whatsapp.send_buttons(
        wa_id, "What would you like to do?", buttons, footer="Type a question or tap an option",
    )


async def tutor_chat(wa_id: str, question: str) -> None:
    cur = state.get_state(wa_id)
    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson = state.current_lesson(cur)
    lesson_id = cur.get("tutor_lesson") or (lesson["id"] if lesson else None)
    lesson_title = lesson["title"] if lesson else f"Module {(cur.get('lesson_index') or 0) + 1}"

    section = curriculum.lesson_as_context(unit_id, lesson_id) if unit_id and lesson_id else ""

    db.log_activity(wa_id, "tutor_query", question[:80])
    answer = await ai_tutor.answer_question(question, section=section, module_title=lesson_title)
    await whatsapp.send_text(wa_id, answer)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    if unit_id:
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
    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson = state.current_lesson(cur) if phase in ("lesson", "quiz") else None
    module_title = lesson["title"] if lesson else ""

    section = ""
    if phase == "lesson" and lesson:
        section = curriculum.lesson_as_context(unit_id, lesson["id"])
    elif phase == "quiz" and lesson:
        section = curriculum.quiz_as_context(unit_id, lesson["id"])

    logger.info("AI fallback (%s) phase=%s: %s", wa_id, phase, question[:120])
    db.log_activity(wa_id, "free_text_ai", question[:80])
    answer = await ai_tutor.answer_question(question, section=section, module_title=module_title)
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
