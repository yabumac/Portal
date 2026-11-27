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
STEP_CONTINUE = "step_continue"
NEXT_STEP = "next_step"
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
    from api.admin import router as admin_router, admin_dashboard, export_users_csv
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

    @app.get("/admin/export/csv")
    @app.get("/admin/export/csv/")
    @app.get("/api/admin/export/csv")
    @app.get("/api/admin/export/csv/")
    @app.get("/export/csv")
    @app.get("/export/csv/")
    async def export_csv_view(request: Request):
        return await export_users_csv(request)

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


def get_clean_request_path(request: Request, path: str = "") -> str:
    """Extract clean request path even behind Vercel serverless rewrites."""
    raw = request.query_params.get("__path__") or path or request.url.path or ""
    clean = raw.strip("/").lower()
    if clean.startswith("api/index.py"):
        clean = clean[len("api/index.py"):].strip("/")
    elif clean.startswith("index.py"):
        clean = clean[len("index.py"):].strip("/")
    return clean


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------
async def _dispatch_admin_get(request: Request, clean_path: str, raw_path: str):
    """Shared GET dispatcher for admin API, CSV export, login/logout, and dashboard under Vercel rewrites."""
    from urllib.parse import unquote

    params = request.query_params
    if clean_path in ("admin/export/csv", "export/csv") or clean_path.endswith("export/csv") or "export/csv" in raw_path:
        from api.admin import export_users_csv
        return await export_users_csv(request)

    if clean_path.startswith("admin/login") or clean_path == "login" or "admin/login" in raw_path:
        from api.admin import login_page
        return await login_page(error=params.get("error"))

    if clean_path in ("admin/logout", "logout"):
        from api.admin import logout
        return await logout()

    if any(k in raw_path or k in clean_path for k in ("admin/api/analytics", "api/admin/analytics", "api/analytics")):
        from api.admin import get_analytics_json
        return await get_analytics_json(request)

    if any(k in raw_path or k in clean_path for k in ("admin/api/test-gemini", "api/admin/test-gemini", "api/test-gemini")):
        from api.admin import test_gemini_endpoint
        return await test_gemini_endpoint(request)

    if any(k in raw_path or k in clean_path for k in ("admin/api/whatsapp-status", "api/admin/whatsapp-status")):
        from api.admin import get_whatsapp_status
        return await get_whatsapp_status(request)

    for prefix in ("admin/api/user/", "api/admin/user/"):
        if clean_path.startswith(prefix):
            phone_part = unquote(clean_path[len(prefix):].strip("/"))
            from api.admin import get_single_user_json
            return await get_single_user_json(phone_part, request)

    if (
        clean_path in ("admin", "dashboard", "admin/dashboard", "api/admin", "api/dashboard")
        or clean_path.startswith("admin/")
        or "admin" in raw_path
        or "dashboard" in raw_path
        or params.get("password")
        or params.get("pass")
    ):
        from api.admin import admin_dashboard
        return await admin_dashboard(request)

    return None


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

    clean_path = get_clean_request_path(request)
    raw_path = (
        request.headers.get("x-matched-path")
        or request.headers.get("x-invoke-path")
        or request.headers.get("x-forwarded-uri")
        or request.headers.get("x-real-path")
        or request.headers.get("x-original-url")
        or clean_path
    ).lower()

    admin_resp = await _dispatch_admin_get(request, clean_path, raw_path)
    if admin_resp is not None:
        return admin_resp

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
    clean_path = get_clean_request_path(request, path)

    # Route admin login POST
    if clean_path.startswith("admin/login") or clean_path == "login":
        from api.admin import login_submit
        return await login_submit(request)

    # Route admin API POST endpoints
    if clean_path.startswith("admin/api/") or clean_path.startswith("api/admin/"):
        from urllib.parse import unquote
        subpath = clean_path
        for prefix in ("admin/api/", "api/admin/"):
            if subpath.startswith(prefix):
                subpath = subpath[len(prefix):]
                break

        if subpath == "broadcast":
            from api.admin import send_broadcast_endpoint
            return await send_broadcast_endpoint(request)
        if subpath == "direct-message":
            from api.admin import send_direct_message_endpoint
            return await send_direct_message_endpoint(request)
        if subpath == "test-whatsapp":
            from api.admin import test_whatsapp_endpoint
            return await test_whatsapp_endpoint(request)
        if subpath.startswith("user/") and subpath.endswith("/reset"):
            phone = unquote(subpath.split("/")[1])
            from api.admin import reset_single_user
            return await reset_single_user(phone, request)
        if subpath.startswith("user/") and subpath.endswith("/delete"):
            phone = unquote(subpath.split("/")[1])
            from api.admin import delete_single_user
            return await delete_single_user(phone, request)

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

    clean_path = get_clean_request_path(request, path)
    raw_path = (
        request.headers.get("x-matched-path")
        or request.headers.get("x-invoke-path")
        or request.headers.get("x-forwarded-uri")
        or request.headers.get("x-real-path")
        or request.headers.get("x-original-url")
        or clean_path
    ).lower()

    admin_resp = await _dispatch_admin_get(request, clean_path, raw_path)
    if admin_resp is not None:
        return admin_resp

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

    # 'menu' -> main menu (soft exit modes)
    if low == "menu":
        if phase == "tutor":
            state.exit_tutor(wa_id)
        elif phase == "assessment":
            state.abort_assessment(wa_id)
        await send_menu(wa_id, fresh=False)
        return

    # tutor mode: act as a free conversational AI chatbot (even on 'hi'/'hello'/'help');
    # explicit exit keywords ('menu', 'exit', 'quit', 'back') or buttons exit tutor mode.
    if phase == "tutor":
        if low in MODE_ABORT:
            await exit_tutor_flow(wa_id)
            return
        await tutor_chat(wa_id, text)
        return

    # greetings -> intro or resume menu (outside tutor mode; exits assessment if active)
    if low in GREETINGS:
        if phase == "assessment":
            state.abort_assessment(wa_id)
        await send_menu(wa_id, fresh=True)
        return

    # assessment mode: A/B/C or 1/2/3 = answer, else prompt retry
    if phase == "assessment":
        num_map = {"1": "A", "2": "B", "3": "C"}
        mapped = num_map.get(low, low.upper())
        if mapped in ("A", "B", "C"):
            await handle_assessment_answer(wa_id, mapped)
            return
        idx = state.assessment_index(wa_id)
        await whatsapp.send_text(wa_id, "Please tap A, B or C below to answer.")
        await send_assessment_question(wa_id, idx)
        return

    # Replay or send video on demand (checks current step video first, then lesson video)
    if low in ("video", "watch video", "watch", "play video", "clip", "replay", "show video", "send video"):
        lesson = state.current_lesson(cur)
        step_idx = cur.get("step_index", 0)
        steps = lesson.get("steps", []) if lesson else []
        active_step = steps[step_idx] if (0 <= step_idx < len(steps)) else None
        vid_file = (active_step.get("video_file") if active_step else None) or (lesson.get("video_file") if lesson else None)
        if vid_file and lesson:
            v_url = get_public_media_url(vid_file)
            step_title = (active_step.get("title") if active_step else None) or lesson["title"]
            cap = (active_step.get("caption") if active_step else None) or lesson.get("caption") or "Watch the lesson video above:"
            await whatsapp.send_media(wa_id, "video", v_url, caption=f"{step_title}\n\n{cap}")
        else:
            await whatsapp.send_text(wa_id, "No video clip is attached to this section. Tap 'Continue' or type 'menu'.")
        return

    # Direct enrollment or start commands
    if low in ("enroll", "start", "begin", "learn", "study", "join", "course"):
        await handle_button_click(wa_id, ENROLL)
        return

    # Direct module jumping constrained to actual available modules
    unit_id_jump = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    total_avail = curriculum.total_lessons(unit_id_jump)
    for mod_num in range(1, total_avail + 1):
        if low in (f"module {mod_num}", f"mod {mod_num}", f"lesson {mod_num}"):
            state.start_unit(wa_id, unit_id_jump, restart=False)
            updated = state.get_state(wa_id)
            if (updated.get("lesson_index") or 0) != (mod_num - 1):
                updated["lesson_index"] = mod_num - 1
                updated["step_index"] = 0
                updated["awaiting_response"] = None
            updated["phase"] = "lesson"
            state.set_state(wa_id, updated)
            lesson = state.current_lesson(updated)
            if lesson:
                await deliver_lesson(wa_id, lesson)
            return

    # lesson phase: check if learner is responding to an interactive reflection question
    if phase == "lesson":
        awaiting = cur.get("awaiting_response")
        if awaiting in ("what_is_ai", "everyday_ai_use"):
            if low in ("continue", "next", "skip", "pass", "idk", "go", "ready", "quiz", "resume"):
                nudge = (
                    "Please type your answer or thoughts about what AI means to you to continue:"
                    if awaiting == "what_is_ai"
                    else "Please type your thoughts on how you use AI (e.g. search, translation, writing, maps) to continue:"
                )
                await whatsapp.send_text(wa_id, nudge)
                return
            await _handle_reflection_submission(wa_id, cur, awaiting, text)
            return

    # lesson or resume shortcuts
    if low in LESSON_GO:
        if phase == "quiz":
            await send_quiz(wa_id)
            return
        elif phase == "lesson":
            await advance_module_step(wa_id)
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

    if button_id in ("main_menu", "menu"):
        await send_menu(wa_id, fresh=False)
        return

    if button_id in (ENROLL, RESUME, STEP_CONTINUE, NEXT_STEP, "continue", "next"):
        cur = state.get_state(wa_id)

        # If already completed all modules, inform learner and do not loop on continue!
        if state.is_course_complete(cur):
            await whatsapp.send_text(
                wa_id,
                "You have already finished all modules of this course! Excellent work.\n\n"
                "There are no further modules to continue. You can ask the AI Tutor questions "
                "or review and restart the course below:",
            )
            await send_menu(wa_id, fresh=False)
            return

        # If user tapped an older lesson/menu button while inside Tutor mode, exit tutor mode cleanly first
        if cur.get("phase") == "tutor":
            state.exit_tutor(wa_id)
            cur = state.get_state(wa_id)

        phase = cur.get("phase")
        if phase == "lesson" and button_id in (STEP_CONTINUE, NEXT_STEP, "continue", "next"):
            await advance_module_step(wa_id)
            return

        lesson_idx = cur.get("lesson_index", 0)
        completed = cur.get("completed_lessons") or []

        # Check if user already has course progress - resume at their exact step/quiz without losing state!
        has_progress = (
            cur.get("phase") in ("lesson", "quiz", "assessment")
            or (lesson_idx is not None and lesson_idx > 0)
            or (cur.get("step_index") or 0) > 0
            or bool(cur.get("quiz_answers"))
            or len(completed) > 0
        )

        if has_progress:
            state.start_unit(wa_id, curriculum.DEFAULT_UNIT_ID, restart=False)
            updated = state.get_state(wa_id)
            lesson = state.current_lesson(updated)
            if updated.get("phase") == "quiz":
                await send_quiz(wa_id)
            elif lesson:
                await deliver_lesson(wa_id, lesson)
            else:
                await recover_or_start(wa_id)
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
        cur = state.get_state(wa_id)
        if state.is_course_complete(cur):
            await recover_or_start(wa_id)
            return
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
        cur = state.get_state(wa_id)
        if state.is_course_complete(cur):
            await recover_or_start(wa_id)
            return
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
    is_completed = state.is_course_complete(cur)

    # Check if user has active or existing progress in the course (and not finished)
    has_progress = (
        not is_completed
        and (
            phase in ("lesson", "quiz", "tutor", "assessment")
            or (lesson_idx is not None and lesson_idx > 0)
            or (cur.get("step_index") or 0) > 0
            or bool(cur.get("quiz_answers"))
            or len(completed) > 0
        )
    )

    if fresh:
        if is_completed:
            await whatsapp.send_text(
                wa_id,
                "Welcome back to EdTech Hub.\n\n"
                "You have completed Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia!\n\n"
                "There are no further modules to continue. You can ask the AI Tutor questions, "
                "or review and restart the module below:",
            )
        elif has_progress:
            lesson = state.current_lesson(cur)
            lesson_title = lesson["title"] if lesson else f"Module {(lesson_idx or 0) + 1}"
            total_mods = curriculum.total_lessons(cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID) or 1
            await whatsapp.send_text(
                wa_id,
                f"Welcome back to EdTech Hub.\n\n"
                f"You are currently on: {lesson_title} (Completed {len(completed)}/{total_mods} modules).\n\n"
                f"Choose an option below to continue where you left off:",
            )
        else:
            # Send welcome video clip (user's provided video instead of edtech logo picture)
            try:
                video_url = get_public_media_url("welcome_video.mp4")
                await whatsapp.send_media(
                    wa_id,
                    "video",
                    video_url,
                    caption="Welcome to AI for Teaching and Learning (Ethiopian Educators Edition)",
                )
                await asyncio.sleep(0.6)
            except Exception as media_err:
                logger.warning("Could not send welcome video (non-blocking): %s", media_err)

            await whatsapp.send_text(wa_id, curriculum.BOT_INTRO)
            await asyncio.sleep(0.3)
    else:
        if is_completed:
            await whatsapp.send_text(
                wa_id,
                "Course Completed:\n\n"
                "You have finished Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia. "
                "There are no further modules to continue. "
                "You can ask the AI Tutor questions, or review and restart the module below:",
            )
        else:
            await whatsapp.send_text(wa_id, "Main menu:")

    if is_completed:
        buttons = [
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": RESTART, "title": "Review / Restart"},
            {"id": ASSESS, "title": "Take Survey"},
        ]
    elif has_progress:
        buttons = [
            {"id": RESUME, "title": "Continue Course"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            {"id": RESTART, "title": "Restart Course"},
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
async def deliver_step(wa_id: str, lesson: dict, step_idx: int) -> None:
    cur = state.get_state(wa_id)
    steps = lesson.get("steps", [])
    if not (0 <= step_idx < len(steps)):
        cur["phase"] = "quiz"
        cur["quiz_question_idx"] = 0
        state.set_state(wa_id, cur)
        await send_quiz(wa_id)
        return

    step = steps[step_idx]

    if step_idx == 0:
        # Step 0: Course Intro, Description, Objectives & Intro Video
        cur["phase"] = "lesson"
        cur["step_index"] = 0
        cur["awaiting_response"] = None
        state.set_state(wa_id, cur)

        for t in step.get("texts", []):
            await whatsapp.send_text(wa_id, t)
            await asyncio.sleep(0.35)

        vid = step.get("video_file")
        if vid:
            try:
                v_url = get_public_media_url(vid)
                cap = step.get("caption") or "Module 1 Introduction: AI for Teaching and Learning"
                await whatsapp.send_media(wa_id, "video", v_url, caption=cap)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning("Failed to send intro video for step 0: %s", e)

        await whatsapp.send_buttons(
            wa_id,
            "Ready to begin Section 1?",
            [
                {"id": STEP_CONTINUE, "title": "Continue"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Tap Continue to proceed",
        )
        return

    if step_idx == 1:
        # Step 1: Section 1: What is AI?
        img = step.get("image_file")
        if img:
            try:
                i_url = get_public_media_url(img)
                await whatsapp.send_media(wa_id, "image", i_url, caption="Section 1: What is Artificial Intelligence?")
                await asyncio.sleep(0.4)
            except Exception as e:
                logger.warning("Failed to send image for step 1: %s", e)

        q_text = step.get("question", "Q: What is AI?")
        note = step.get("prompt_note", "Take a moment to type your answer or thoughts about what AI means to you below:")
        await whatsapp.send_text(wa_id, f"{q_text}\n\n{note}")
        await asyncio.sleep(0.3)

        cur["awaiting_response"] = "what_is_ai"
        cur["step_index"] = 1
        state.set_state(wa_id, cur)

        await whatsapp.send_buttons(
            wa_id,
            "Please type your answer in the chat box below:",
            [
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Type your answer to continue",
        )
        return

    if step_idx == 2:
        # Step 2: Section 1: Everyday AI
        for t in step.get("texts", []):
            await whatsapp.send_text(wa_id, t)
            await asyncio.sleep(0.3)

        img = step.get("image_file")
        if img:
            try:
                i_url = get_public_media_url(img)
                await whatsapp.send_media(wa_id, "image", i_url, caption="Simple Examples of AI in Everyday Life")
                await asyncio.sleep(0.4)
            except Exception as e:
                logger.warning("Failed to send image for step 2: %s", e)

        q_text = step.get("question", "Q: For what purposes do you use AI in your daily life?")
        note = step.get("prompt_note", "Type your answer below (e.g. search, translation, writing, maps):")
        await whatsapp.send_text(wa_id, f"{q_text}\n\n{note}")
        await asyncio.sleep(0.3)

        cur["awaiting_response"] = "everyday_ai_use"
        cur["step_index"] = 2
        state.set_state(wa_id, cur)

        await whatsapp.send_buttons(
            wa_id,
            "Please type your answer in the chat box below:",
            [
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Type your answer to continue",
        )
        return

    if step_idx == 3:
        # Step 3: Section 2: Overview of AI in Education
        for t in step.get("texts", []):
            await whatsapp.send_text(wa_id, t)
            await asyncio.sleep(0.35)

        vid = step.get("video_file")
        if vid:
            try:
                v_url = get_public_media_url(vid)
                cap = step.get("caption") or "Section 2: Overview of AI in Education"
                await whatsapp.send_media(wa_id, "video", v_url, caption=cap)
                await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning("Failed to send video for step 3: %s", e)

        img_list = step.get("image_files", [])
        captions = ["AI in Education", "Opportunities and Limitations of AI"]
        for idx, im in enumerate(img_list):
            try:
                i_url = get_public_media_url(im)
                cap = captions[idx] if idx < len(captions) else "AI in Education"
                await whatsapp.send_media(wa_id, "image", i_url, caption=cap)
                await asyncio.sleep(0.4)
            except Exception as e:
                logger.warning("Failed to send image for step 3: %s", e)

        cur["awaiting_response"] = None
        cur["step_index"] = 3
        state.set_state(wa_id, cur)

        await whatsapp.send_buttons(
            wa_id,
            "Module 1 sections complete! Ready to start the quiz?",
            [
                {"id": READY_QUIZ, "title": "Start Quiz"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Test your knowledge or ask a question",
        )
        return


async def _handle_reflection_submission(wa_id: str, cur: dict, awaiting: str, text: str) -> None:
    """Evaluate a learner's short reflection answer with real-time AI coaching + official answer."""
    configs = {
        "what_is_ai": {
            "log_prefix": "What is AI",
            "question": "Q: What is AI?",
            "reference": (
                "Artificial Intelligence (AI) is a technology that enables computers and machines "
                "to perform tasks that normally require human intelligence, such as learning from information, "
                "recognizing patterns, understanding language and generating content."
            ),
            "next_prompt": "Ready to continue to everyday AI examples?",
        },
        "everyday_ai_use": {
            "log_prefix": "Everyday AI",
            "question": "Q: For what purposes do you use AI in your daily life?",
            "reference": (
                "AI tools are already part of our everyday lives (such as voice assistants, Google Maps routes, "
                "language translation, face recognition, and ChatGPT), making activities easier, faster, and more convenient."
            ),
            "next_prompt": "Ready for Section 2 (Overview of AI in Education)?",
        },
    }
    cfg = configs[awaiting]
    cur["awaiting_response"] = None
    state.set_state(wa_id, cur)
    db.log_activity(wa_id, "interactive_response", f"{cfg['log_prefix']}: {text[:100]}")

    feedback_msg = await ai_tutor.evaluate_reflection(
        question=cfg["question"],
        user_answer=text,
        reference_answer=cfg["reference"],
        mode=awaiting,
    )
    state.record_reflection_answer(wa_id, awaiting, text, feedback_msg)

    await whatsapp.send_text(wa_id, feedback_msg)
    await asyncio.sleep(0.4)
    await whatsapp.send_buttons(
        wa_id,
        cfg["next_prompt"],
        [
            {"id": STEP_CONTINUE, "title": "Continue"},
            {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
        ],
        footer="Tap Continue to proceed",
    )


async def advance_module_step(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson = state.current_lesson(cur)
    if not lesson:
        await recover_or_start(wa_id)
        return

    steps = lesson.get("steps")
    if not steps:
        # Fallback for standard lesson without steps
        cur["phase"] = "quiz"
        state.set_state(wa_id, cur)
        await send_quiz(wa_id)
        return

    step_idx = cur.get("step_index", 0)
    awaiting = cur.get("awaiting_response")

    # Enforce typed reflection: user must type their answer before continuing
    if awaiting in ("what_is_ai", "everyday_ai_use"):
        await whatsapp.send_text(
            wa_id,
            "Please type your answer to the question in the chat box above to continue.",
        )
        return

    next_step = step_idx + 1

    # Fit the 4-question AI Readiness Survey cleanly right after Course Intro (Step 0) -> before Section 1
    if step_idx == 0 and next_step == 1:
        assess_ans = cur.get("assessment_answers") or {}
        if len(assess_ans) < len(curriculum.ASSESSMENT):
            state.start_assessment(wa_id, return_to="step_1")
            await whatsapp.send_text(
                wa_id,
                "Before we begin Section 1, please answer 4 quick survey questions to tailor your learning experience:",
            )
            await asyncio.sleep(0.3)
            await send_assessment_question(wa_id, 0)
            return

    if next_step < len(steps):
        cur["step_index"] = next_step
        state.set_state(wa_id, cur)
        await deliver_step(wa_id, lesson, next_step)
    else:
        # All sections viewed -> go to quiz
        cur["phase"] = "quiz"
        cur["quiz_question_idx"] = 0
        state.set_state(wa_id, cur)
        await send_quiz(wa_id)


async def deliver_lesson(wa_id: str, lesson) -> None:
    if lesson is None:
        await recover_or_start(wa_id)
        return

    db.log_activity(wa_id, "lesson_viewed", lesson.get("title", ""))

    cur = state.get_state(wa_id)
    steps = lesson.get("steps")
    if steps:
        step_idx = cur.get("step_index", 0)
        await deliver_step(wa_id, lesson, step_idx)
        return

    # Standard video & picture delivery for modules without steps
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

    for paragraph in lesson.get("body", []):
        await whatsapp.send_text(wa_id, paragraph)
        await asyncio.sleep(0.3)

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
# Quiz (Multi-question support with hints)
# ---------------------------------------------------------------------------
async def send_quiz(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    lesson = state.current_lesson(cur)

    if not lesson:
        await recover_or_start(wa_id)
        return

    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    quiz_questions = curriculum.get_quiz_questions(unit_id, lesson["id"])
    if not quiz_questions:
        await whatsapp.send_text(wa_id, "No quiz for this lesson. Moving forward:")
        outcome, next_lesson = state.advance_past_lesson(wa_id)
        if outcome == "lesson":
            await deliver_lesson(wa_id, next_lesson)
        else:
            await send_menu(wa_id, fresh=False)
        return

    q_idx = cur.get("quiz_question_idx", 0)
    if q_idx >= len(quiz_questions):
        q_idx = 0
        cur["quiz_question_idx"] = 0
        state.set_state(wa_id, cur)

    quiz = quiz_questions[q_idx]
    total_q = len(quiz_questions)

    options = quiz["options"]
    body = quiz["question"]
    for key in options:
        body += f"\n\n{key}) {options[key]}"

    header_label = f"Quiz ({q_idx + 1}/{total_q}) - {lesson['title']}"
    if len(header_label) > 60:
        header_label = f"Quiz ({q_idx + 1}/{total_q})"

    await whatsapp.send_buttons(
        wa_id,
        body,
        [{"id": f"{ANSWER_PREFIX}{key}", "title": key} for key in options],
        header=header_label,
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
    quiz_questions = curriculum.get_quiz_questions(unit_id, lesson_id)
    q_idx = cur.get("quiz_question_idx", 0)

    if not curriculum.is_valid_option(unit_id, lesson_id, answer, question_idx=q_idx):
        quiz = curriculum.get_quiz(unit_id, lesson_id, question_idx=q_idx)
        opts_hint = ", ".join(quiz["options"].keys()) if quiz else "your choice"
        await whatsapp.send_text(wa_id, f"Please tap {opts_hint} below.")
        await send_quiz(wa_id)
        return

    result = curriculum.check_answer(unit_id, lesson_id, answer, question_idx=q_idx)
    explanation = result["explanation"]

    # Record result in state and activity log
    state.record_quiz_result(wa_id, lesson_id, answer, result["correct"], question_idx=q_idx)

    if result["correct"]:
        total_q = len(quiz_questions)
        next_q = q_idx + 1
        if next_q < total_q:
            cur["quiz_question_idx"] = next_q
            state.set_state(wa_id, cur)
            await whatsapp.send_text(
                wa_id,
                f"Correct! {explanation}\n\nMoving to Question {next_q + 1} of {total_q}:",
            )
            await asyncio.sleep(0.4)
            await send_quiz(wa_id)
            return
        else:
            # All questions in this module completed!
            await whatsapp.send_text(wa_id, f"Correct! {explanation}")
            await asyncio.sleep(0.4)

            # Module closing message
            closing_msg = lesson.get("closing") or curriculum.MODULE_1_CLOSING
            await whatsapp.send_text(wa_id, closing_msg)
            await asyncio.sleep(0.5)

            outcome, next_lesson = state.advance_past_lesson(wa_id)
            if outcome == "lesson":
                await deliver_lesson(wa_id, next_lesson)
            else:
                updated = state.get_state(wa_id)
                has_survey = len(updated.get("assessment_answers") or {}) >= len(curriculum.ASSESSMENT)
                end_buttons = [
                    {"id": "main_menu", "title": "Main Menu"},
                    {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                    {"id": RESTART if has_survey else ASSESS, "title": "Review / Restart" if has_survey else "Take Survey"},
                ]
                await whatsapp.send_buttons(
                    wa_id,
                    "Course Complete! Choose an option below:",
                    end_buttons,
                    header="Course Complete",
                    footer="Tap an option",
                )
            return
    else:
        hint_msg = result.get("hint") or "Review the lesson materials and key principles, then try again."
        await whatsapp.send_text(
            wa_id,
            f"Not quite. Here is a helpful hint:\n\n{hint_msg}\n\nPlease try again below:",
        )
        await send_quiz(wa_id)
        return


# ---------------------------------------------------------------------------
# AI Tutor mode
# ---------------------------------------------------------------------------
async def enter_tutor_flow(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    lesson = state.current_lesson(cur)
    lesson_id = lesson["id"] if lesson else None
    context_label = lesson["title"] if lesson else "Module 1: AI Basics and The Teacher as Editor"
    is_completed = state.is_course_complete(cur)

    state.enter_tutor(wa_id, lesson_id=lesson_id)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    # Only offer "Continue Course" if the user has NOT finished all modules
    if not is_completed and (cur.get("unit_id") or cur.get("tutor_resume")):
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
    active_lesson_id = cur.get("tutor_lesson") or (lesson["id"] if lesson else None)
    active_lesson = curriculum.get_lesson(unit_id, active_lesson_id) if (unit_id and active_lesson_id) else lesson
    lesson_title = active_lesson["title"] if active_lesson else (lesson["title"] if lesson else f"Module {(cur.get('lesson_index') or 0) + 1}")
    is_completed = state.is_course_complete(cur)

    section = curriculum.lesson_as_context(unit_id, active_lesson_id) if unit_id and active_lesson_id else ""

    db.log_activity(wa_id, "tutor_query", question[:80])
    history = cur.get("tutor_history") or []
    answer = await ai_tutor.answer_question(question, section=section, module_title=lesson_title, history=history)
    state.append_tutor_turn(wa_id, question, answer)
    await whatsapp.send_text(wa_id, answer)

    buttons = [{"id": EXIT_TUTOR, "title": "Exit Tutor"}]
    # Only offer "Continue Course" if the user has NOT finished all modules
    if not is_completed and unit_id:
        buttons.append({"id": TUTOR_RESUME, "title": "Continue Course"})

    await whatsapp.send_buttons(
        wa_id, "What next?", buttons, footer="Ask more or exit",
    )


async def _send_lesson_resume_prompt(wa_id: str, cur: dict, lesson: dict) -> None:
    """
    Send the exact interactive continuation prompt for the learner's current step/awaiting state.
    Never jumps ahead to the quiz unless all sections are completed.
    """
    steps = lesson.get("steps") or []
    if not steps:
        await whatsapp.send_text(wa_id, f"Back to your lesson: {lesson['title']}")
        await whatsapp.send_buttons(
            wa_id,
            "What would you like to do?",
            [
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                {"id": READY_QUIZ, "title": "Continue to Quiz"},
            ],
            footer="Ask a question or continue to the quiz",
        )
        return

    step_idx = cur.get("step_index", 0)
    awaiting = cur.get("awaiting_response")

    if step_idx == 0:
        await whatsapp.send_buttons(
            wa_id,
            "Back to Module 1 Introduction. Ready to begin Section 1?",
            [
                {"id": STEP_CONTINUE, "title": "Continue"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Tap Continue to proceed",
        )
    elif step_idx == 1:
        if awaiting == "what_is_ai":
            step = steps[1]
            q_text = step.get("question", "Q: What is AI?")
            note = step.get("prompt_note", "Take a moment to type your answer or thoughts about what AI means to you below:")
            await whatsapp.send_text(wa_id, f"Back to Section 1:\n\n{q_text}\n\n{note}")
            await whatsapp.send_buttons(
                wa_id,
                "Please type your answer in the chat box below:",
                [{"id": ASK_TUTOR, "title": "Ask AI Tutor"}],
                footer="Type your answer to continue",
            )
        else:
            await whatsapp.send_buttons(
                wa_id,
                "Back to Section 1. Ready to continue to everyday AI examples?",
                [
                    {"id": STEP_CONTINUE, "title": "Continue"},
                    {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                ],
                footer="Tap Continue to proceed",
            )
    elif step_idx == 2:
        if awaiting == "everyday_ai_use":
            step = steps[2]
            q_text = step.get("question", "Q: For what purposes do you use AI in your daily life?")
            note = step.get("prompt_note", "Type your answer below (e.g. search, translation, writing, maps):")
            await whatsapp.send_text(wa_id, f"Back to Section 1 (Everyday AI):\n\n{q_text}\n\n{note}")
            await whatsapp.send_buttons(
                wa_id,
                "Please type your answer in the chat box below:",
                [{"id": ASK_TUTOR, "title": "Ask AI Tutor"}],
                footer="Type your answer to continue",
            )
        else:
            await whatsapp.send_buttons(
                wa_id,
                "Back to Section 1. Ready for Section 2 (Overview of AI in Education)?",
                [
                    {"id": STEP_CONTINUE, "title": "Continue"},
                    {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                ],
                footer="Tap Continue to proceed",
            )
    else:
        await whatsapp.send_buttons(
            wa_id,
            "Module 1 sections complete! Ready to start the quiz?",
            [
                {"id": READY_QUIZ, "title": "Start Quiz"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Test your knowledge or ask a question",
        )


async def exit_tutor_flow(wa_id: str) -> None:
    """Exit tutor and return directly to where the learner left off."""
    cur = state.get_state(wa_id)
    unit_id = cur.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    resume_lesson_id = cur.get("tutor_lesson")
    resume = state.exit_tutor(wa_id)
    updated = state.get_state(wa_id)

    if resume == "lesson" and unit_id:
        lesson = (
            curriculum.get_lesson(unit_id, resume_lesson_id)
            if resume_lesson_id
            else state.current_lesson(updated)
        )
        if lesson:
            await _send_lesson_resume_prompt(wa_id, updated, lesson)
            return

    if resume == "quiz" and unit_id:
        await send_quiz(wa_id)
        return

    await send_menu(wa_id, fresh=False)


async def resume_from_tutor(wa_id: str) -> None:
    cur = state.get_state(wa_id)
    if state.is_course_complete(cur):
        await whatsapp.send_text(
            wa_id,
            "You have completed Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia! Returning to the main menu.",
        )
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
        if result.get("return_to") == "step_1":
            await whatsapp.send_text(
                wa_id,
                "Thank you for sharing! Now let's begin Section 1:",
            )
            await asyncio.sleep(0.4)
            updated = state.get_state(wa_id)
            lesson = state.current_lesson(updated)
            if lesson:
                await deliver_step(wa_id, lesson, 1)
                return
        await whatsapp.send_text(
            wa_id,
            "Thank you for completing the AI Self-Assessment!\n\n"
            "Your responses have been recorded to help improve teacher support.",
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
        await _send_lesson_resume_prompt(wa_id, cur, lesson)
    elif phase == "quiz" and lesson:
        await send_quiz(wa_id)
    elif phase == "complete" or state.is_course_complete(cur):
        await whatsapp.send_buttons(
            wa_id,
            "You have completed Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia!",
            [
                {"id": "main_menu", "title": "Main Menu"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
                {"id": RESTART, "title": "Review / Restart"},
            ],
            footer="Tap an option or keep chatting",
        )
    else:
        await whatsapp.send_buttons(
            wa_id,
            "What would you like to do next?",
            [
                {"id": ENROLL, "title": "Enroll in Course"},
                {"id": "main_menu", "title": "Main Menu"},
                {"id": ASK_TUTOR, "title": "Ask AI Tutor"},
            ],
            footer="Tap an option or keep chatting",
        )


# ---------------------------------------------------------------------------
# Graceful state recovery (database backed)
# ---------------------------------------------------------------------------
async def recover_or_start(wa_id: str) -> None:
    """Seamlessly load user progress from database without resetting."""
    cur = state.get_state(wa_id)
    if state.is_course_complete(cur):
        await whatsapp.send_text(
            wa_id,
            "You have already completed Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia!\n\n"
            "There are no further modules to continue. You can ask the AI Tutor questions, "
            "or review and restart the module below:",
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
