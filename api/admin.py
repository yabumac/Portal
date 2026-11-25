"""
api/admin.py - Modern Enterprise Admin & Analytics Dashboard for EdTech Hub.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
import os
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Cookie, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from bot import db, state
from content import curriculum

router = APIRouter()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SESSION_COOKIE_NAME = "portal_admin_session"


def is_authenticated(request: Request) -> bool:
    """Check if admin is authenticated via cookie, query param, or header."""
    if not ADMIN_PASSWORD:
        return True

    # Check query param (?password=... or ?pass=...)
    q_pass = request.query_params.get("password") or request.query_params.get("pass")
    if q_pass and q_pass == ADMIN_PASSWORD:
        return True

    # Check header (x-admin-password: ...)
    h_pass = request.headers.get("x-admin-password")
    if h_pass and h_pass == ADMIN_PASSWORD:
        return True

    # Check cookie
    cookie_pass = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_pass and cookie_pass == ADMIN_PASSWORD:
        return True

    return False


@router.get("/logo.png")
async def admin_logo():
    """Serve the EDTECH company logo."""
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media", "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    return Response(status_code=404)


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: Optional[str] = None):
    error_banner = f"""
    <div style="background:#fee2e2;border:1px solid #ef4444;color:#b91c1c;padding:12px 16px;border-radius:10px;margin-bottom:18px;font-size:14px;display:flex;align-items:center;gap:8px;">
        <svg style="width:16px;height:16px;flex-shrink:0;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        <span>{error}</span>
    </div>
    """ if error else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EdTech Portal - Admin Sign In</title>
    <link rel="icon" type="image/png" href="/media/logo.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.45);
            max-width: 420px;
            width: 100%;
            padding: 40px 36px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            position: relative;
            overflow: hidden;
        }}
        .card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 5px;
            background: linear-gradient(90deg, #1d4ed8, #3b82f6, #06b6d4);
        }}
        .brand-header {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            margin-bottom: 28px;
        }}
        .logo-img {{
            width: 80px;
            height: 80px;
            border-radius: 50%;
            object-fit: contain;
            margin-bottom: 16px;
            box-shadow: 0 8px 20px rgba(29, 78, 216, 0.25);
            background: #ffffff;
            padding: 4px;
            border: 2px solid #e2e8f0;
        }}
        .brand-title {{
            font-size: 24px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.5px;
        }}
        .brand-subtitle {{
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
            font-weight: 500;
        }}
        label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: #334155;
            margin-bottom: 8px;
        }}
        .input-group {{
            position: relative;
            margin-bottom: 20px;
        }}
        input[type="password"] {{
            width: 100%;
            padding: 13px 16px;
            border: 1.5px solid #cbd5e1;
            border-radius: 10px;
            font-size: 15px;
            outline: none;
            transition: all 0.2s ease;
            font-family: inherit;
        }}
        input[type="password"]:focus {{
            border-color: #2563eb;
            box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.15);
        }}
        button {{
            width: 100%;
            padding: 13px;
            background: #1d4ed8;
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(29, 78, 216, 0.3);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        button:hover {{
            background: #1e40af;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(29, 78, 216, 0.4);
        }}
        .footer-note {{
            font-size: 12px;
            color: #94a3b8;
            text-align: center;
            margin-top: 24px;
            line-height: 1.5;
        }}
        .footer-note code {{
            background: #f1f5f9;
            padding: 2px 6px;
            border-radius: 4px;
            color: #334155;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="brand-header">
            <img src="/media/logo.png" alt="EDTECH Logo" class="logo-img" onerror="this.src='/logo.png'">
            <h1 class="brand-title">EDTECH PORTAL</h1>
            <p class="brand-subtitle">Teacher Learning Management & Real-Time Analytics</p>
        </div>
        {error_banner}
        <form method="post" action="/admin/login">
            <div class="input-group">
                <label for="password">Administrator Password</label>
                <input type="password" id="password" name="password" required autofocus placeholder="Enter your password">
            </div>
            <button type="submit">
                <span>Sign In to Dashboard</span>
                <span>&rarr;</span>
            </button>
        </form>
        <p class="footer-note">
            Default security key: <code>admin123</code><br>
            (Configurable in environment via <code>ADMIN_PASSWORD</code>)
        </p>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.post("/login")
async def process_login(request: Request):
    body = await request.body()
    try:
        parsed = parse_qs(body.decode("utf-8"))
        password = parsed.get("password", [""])[0]
    except Exception:
        password = ""

    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=password,
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=True,
            samesite="lax",
        )
        return response
    return RedirectResponse(url="/admin/login?error=Invalid%20admin%20password", status_code=status.HTTP_302_FOUND)


# Alias for compatibility with external router invocations
login_submit = process_login


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/api/analytics")
async def get_analytics_json(request: Request):
    """Real-time JSON endpoint for client-side live polling and automatic sync."""
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return db.get_analytics_summary()


@router.get("/api/user/{phone_number}")
async def get_single_user_json(phone_number: str, request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    user = db.get_user_state(phone_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    history = db.get_activity_logs(limit=100, phone_number=phone_number)
    return {"user": user, "history": history}


@router.post("/api/user/{phone_number}/reset")
async def reset_single_user(phone_number: str, request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    state.reset(phone_number)
    return {"status": "ok", "message": f"User {phone_number} reset successfully"}


@router.delete("/api/user/{phone_number}")
@router.post("/api/user/{phone_number}/delete")
async def delete_single_user(phone_number: str, request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    state.del_state(phone_number)
    return {"status": "ok", "message": f"User {phone_number} deleted successfully"}


@router.post("/api/test-whatsapp")
async def test_whatsapp_endpoint(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        body = await request.json()
        phone = body.get("phone", "").strip()
        from bot import whatsapp
        res = await whatsapp.send_test_message(phone)
        return JSONResponse(res)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e), "hint": "Check phone number format and server logs."})


def _format_personalized_message(raw_message: str, phone: str, user: Optional[dict]) -> str:
    """Replace {phone}, {status}, and {progress} tags for an educator."""
    u = user or {}
    phase = u.get("phase", "active")
    is_grad = phase == "complete" or len(u.get("completed_lessons") or []) >= 1
    phase_label = "Graduated" if is_grad else phase.capitalize()
    progress_str = "100%" if is_grad else ("50%" if phase == "quiz" else "0%")
    return (
        raw_message
        .replace("{phone}", phone)
        .replace("{status}", phase_label)
        .replace("{progress}", progress_str)
    )


async def _deliver_admin_message(phone: str, body: str, event_prefix: str, context_label: str) -> dict:
    """
    Send a custom WhatsApp message to an educator with structured Meta diagnostics
    and automatic template fallback when WHATSAPP_REENGAGEMENT_TEMPLATE is configured.
    """
    from bot import whatsapp

    cleaned_phone = "".join(ch for ch in str(phone) if ch.isdigit()) or phone.strip()
    try:
        resp = await whatsapp.send_text(cleaned_phone, body)
        if resp.status_code < 400:
            db.log_activity(phone, f"{event_prefix}_sent", f"{context_label}: {body[:60]}")
            return {"phone": phone, "status": "sent"}

        parsed = whatsapp.parse_meta_error(resp.text)
        template_name = os.getenv("WHATSAPP_REENGAGEMENT_TEMPLATE", "").strip()
        template_lang = os.getenv("WHATSAPP_TEMPLATE_LANG", "en_US").strip() or "en_US"

        # If rejected for >24h window and an approved template is configured, dispatch via template
        if parsed.get("code") == 131047 and template_name:
            params = None if template_name == "hello_world" else [body[:1024]]
            t_resp = await whatsapp.send_template(
                cleaned_phone, template_name, language_code=template_lang, body_params=params
            )
            if t_resp.status_code < 400:
                db.log_activity(phone, f"{event_prefix}_sent", f"{context_label} [template:{template_name}]: {body[:50]}")
                return {"phone": phone, "status": "sent", "used_template": template_name}
            parsed = whatsapp.parse_meta_error(t_resp.text)

        err_msg = parsed.get("hint") or parsed.get("message") or f"HTTP {resp.status_code}"
        db.log_activity(phone, f"{event_prefix}_failed", f"HTTP {resp.status_code}: {err_msg[:80]}")
        return {
            "phone": phone,
            "status": "failed",
            "code": parsed.get("code"),
            "error": err_msg,
            "detail": parsed.get("message"),
        }
    except Exception as exc:
        db.log_activity(phone, f"{event_prefix}_error", str(exc))
        return {"phone": phone, "status": "failed", "error": str(exc)}


@router.post("/api/broadcast")
async def send_broadcast_endpoint(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)

    target_segment = (data.get("segment") or "all").lower().strip()
    raw_message = (data.get("message") or "").strip()

    if not raw_message:
        return JSONResponse({"success": False, "error": "Message text cannot be empty."}, status_code=400)

    all_users = db.get_all_users()
    recipients = []
    for phone, u in all_users.items():
        phase = u.get("phase", "idle")
        completed = u.get("completed_lessons") or []
        is_grad = phase == "complete" or len(completed) >= 1

        if target_segment == "all":
            recipients.append((phone, u))
        elif target_segment == "active" and (phase in ("lesson", "quiz", "tutor") and not is_grad):
            recipients.append((phone, u))
        elif target_segment == "completed" and is_grad:
            recipients.append((phone, u))
        elif target_segment == "idle" and phase == "idle":
            recipients.append((phone, u))

    if not recipients:
        return JSONResponse({
            "success": False,
            "error": f"No educators found in target cohort '{target_segment}'.",
        }, status_code=400)

    sem = asyncio.Semaphore(5)

    async def _send_one(phone: str, u: dict) -> dict:
        async with sem:
            body = _format_personalized_message(raw_message, phone, u)
            return await _deliver_admin_message(phone, body, "admin_broadcast", f"Cohort ({target_segment})")

    results = await asyncio.gather(*(_send_one(p, u) for p, u in recipients))
    sent_count = sum(1 for r in results if r["status"] == "sent")
    failed_count = len(results) - sent_count

    return JSONResponse({
        "success": True,
        "segment": target_segment,
        "total_targets": len(recipients),
        "sent_count": sent_count,
        "failed_count": failed_count,
        "results": results,
    })


@router.post("/api/direct-message")
async def send_direct_message_endpoint(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "Invalid JSON body"}, status_code=400)

    raw_phone = (data.get("phone") or "").strip()
    phone = "".join(ch for ch in raw_phone if ch.isdigit())
    raw_message = (data.get("message") or "").strip()

    if not phone:
        return JSONResponse({"success": False, "error": "Recipient phone number is required."}, status_code=400)
    if not raw_message:
        return JSONResponse({"success": False, "error": "Message text cannot be empty."}, status_code=400)

    user = db.get_user_state(raw_phone) or db.get_user_state(phone) or db.get_user_state(f"+{phone}") or {}
    body = _format_personalized_message(raw_message, raw_phone or phone, user)

    outcome = await _deliver_admin_message(phone, body, "admin_direct_message", "Direct msg")
    if outcome["status"] == "sent":
        return JSONResponse({
            "success": True,
            "phone": phone,
            "used_template": outcome.get("used_template"),
            "message": f"Message delivered successfully to {phone}",
        })
    status_code = 400 if outcome.get("code") else 500
    return JSONResponse({
        "success": False,
        "phone": phone,
        "code": outcome.get("code"),
        "error": outcome.get("error") or "Failed to send message",
        "detail": outcome.get("detail"),
    }, status_code=status_code)


@router.get("/api/test-gemini")
async def test_gemini_endpoint(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from bot import ai_tutor
    diagnostics = await ai_tutor.diagnose_gemini()
    return JSONResponse(diagnostics)


@router.get("/api/whatsapp-status")
async def get_whatsapp_status(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    from bot import whatsapp
    status = whatsapp.get_connection_status()
    return JSONResponse(status)


@router.get("/export/csv")
async def export_users_csv(request: Request):
    if not is_authenticated(request):
        q_pass = request.query_params.get("password") or request.query_params.get("pass")
        if q_pass and q_pass == ADMIN_PASSWORD:
            pass
        else:
            return RedirectResponse(url="/admin/login")

    users = db.get_all_users()
    from content import curriculum

    # Survey mapping
    assessment_map = {}
    for item in getattr(curriculum, "ASSESSMENT", []):
        assessment_map[item.get("id")] = {
            "question": item.get("question", ""),
            "options": item.get("options", {})
        }

    # Lessons mapping
    lessons_list = curriculum.UNITS.get("unit_1", {}).get("lessons", [])

    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM for Microsoft Excel compatibility
    writer = csv.writer(output)

    # Detailed Header Row (1-Module Curriculum)
    headers = [
        "Phone Number (WhatsApp)",
        "Learner Status / Phase",
        "Modules Completed Count",
        "Progress (%)",
        "Current Module Title",
        "Self-Assessment Status",
        "Assessment Q1: AI Usage",
        "Assessment Q2: Classroom Confidence",
        "Assessment Q3: Primary Constraint",
        "Assessment Q4: Main Course Goal",
        "Module 1 Q1 (What is AI)",
        "Module 1 Q2 (Generative AI Example)",
        "Module 1 Q3 (Can AI Be Trusted)",
        "Quiz Score Summary (Correct/Attempted)",
        "Total Messages / Interactions",
        "First Seen / Registered (UTC)",
        "Last Active (UTC)",
        "Raw Assessment Answers JSON",
        "Raw Quiz Answers JSON",
        "Completed Lessons Array"
    ]
    writer.writerow(headers)

    for phone, u in users.items():
        phase = u.get("phase", "idle")
        completed = u.get("completed_lessons") or []
        comp_count = len(completed)

        # Progress calculation for 1-module course
        if phase == "complete" or comp_count >= 1:
            progress_pct = "100%"
            curr_module_title = "Course Completed (Module 1 Finished)"
        elif phase == "quiz":
            progress_pct = "50%"
            curr_module_title = "Module 1: Quiz"
        elif phase == "lesson":
            step_i = u.get("step_index", 0)
            progress_pct = f"{min(45, (step_i + 1) * 15)}%"
            curr_module_title = "Module 1: Understanding Artificial Intelligence (AI)"
        else:
            progress_pct = "0%"
            curr_module_title = "Module 1: Understanding Artificial Intelligence (AI)"

        # Assessment Answers breakdown
        assess = u.get("assessment_answers") or {}
        has_assessment = bool(assess and any(k in assess for k in ("ai_use", "comfort", "challenge", "goal")))
        assess_status = "Completed" if has_assessment else "Not Started"

        q1_val = assess.get("ai_use", "")
        q1_opt = assessment_map.get("ai_use", {}).get("options", {}).get(q1_val, "")
        q1_text = f"{q1_val}: {q1_opt}" if q1_val else "Not answered"

        q2_val = assess.get("comfort", "")
        q2_opt = assessment_map.get("comfort", {}).get("options", {}).get(q2_val, "")
        q2_text = f"{q2_val}: {q2_opt}" if q2_val else "Not answered"

        q3_val = assess.get("challenge", "")
        q3_opt = assessment_map.get("challenge", {}).get("options", {}).get(q3_val, "")
        q3_text = f"{q3_val}: {q3_opt}" if q3_val else "Not answered"

        q4_val = assess.get("goal", "")
        q4_opt = assessment_map.get("goal", {}).get("options", {}).get(q4_val, "")
        q4_text = f"{q4_val}: {q4_opt}" if q4_val else "Not answered"

        # Quiz Answers breakdown (Module 1 Q1, Q2, Q3)
        quizzes = u.get("quiz_answers") or {}
        mod_quiz_cols = []
        correct_count = 0
        attempted_count = 0

        # Module 1 Q1
        m1_q1 = quizzes.get("lesson_1_q1") or quizzes.get("lesson_1")
        if m1_q1:
            attempted_count += 1
            if m1_q1.get("correct"):
                correct_count += 1
                mod_quiz_cols.append(f"{m1_q1.get('answer', '')} (Correct)")
            else:
                mod_quiz_cols.append(f"{m1_q1.get('answer', '')} (Incorrect)")
        else:
            mod_quiz_cols.append("Not attempted")

        # Module 1 Q2
        m1_q2 = quizzes.get("lesson_1_q2")
        if m1_q2:
            attempted_count += 1
            if m1_q2.get("correct"):
                correct_count += 1
                mod_quiz_cols.append(f"{m1_q2.get('answer', '')} (Correct)")
            else:
                mod_quiz_cols.append(f"{m1_q2.get('answer', '')} (Incorrect)")
        else:
            mod_quiz_cols.append("Not attempted")

        # Module 1 Q3
        m1_q3 = quizzes.get("lesson_1_q3")
        if m1_q3:
            attempted_count += 1
            if m1_q3.get("correct"):
                correct_count += 1
                mod_quiz_cols.append(f"{m1_q3.get('answer', '')} (Correct)")
            else:
                mod_quiz_cols.append(f"{m1_q3.get('answer', '')} (Incorrect)")
        else:
            mod_quiz_cols.append("Not attempted")

        quiz_summary_str = f"{correct_count}/{attempted_count} correct" if attempted_count > 0 else "0/0 attempted"

        row = [
            phone,
            phase,
            f"{comp_count} / 1",
            progress_pct,
            curr_module_title,
            assess_status,
            q1_text,
            q2_text,
            q3_text,
            q4_text,
            *mod_quiz_cols,
            quiz_summary_str,
            u.get("total_messages", 0),
            u.get("created_at", ""),
            u.get("last_seen", ""),
            json.dumps(assess, ensure_ascii=False),
            json.dumps(quizzes, ensure_ascii=False),
            json.dumps(completed, ensure_ascii=False),
        ]
        writer.writerow(row)

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=edtech_learners_report.csv",
            "Content-Type": "text/csv; charset=utf-8"
        }
    )


@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")

    data = db.get_analytics_summary()
    summary = data["summary"]
    users_list = data["users"]
    recent_activity = data["recent_activity"]
    backend = data["backend"]
    raw_db_path = str(data.get("database_path") or "portal.db").replace("\\", "/")
    db_path = raw_db_path.split("/")[-1] if raw_db_path else "portal.db"

    from bot import whatsapp
    meta_status = whatsapp.get_connection_status()
    token_ok = meta_status["token_configured"]
    phone_ok = meta_status["phone_configured"]
    token_badge = "badge-green" if token_ok else "badge-orange"
    token_text = meta_status["token_masked"] if token_ok else "MISSING in Vercel"
    phone_badge = "badge-green" if phone_ok else "badge-orange"
    phone_text = meta_status["phone_masked"] if phone_ok else "MISSING in Vercel"
    verify_token_text = meta_status["verify_token"]

    base_url = str(request.base_url).rstrip("/")
    if "vercel.app" in base_url and base_url.startswith("http://"):
        base_url = "https://" + base_url[len("http://"):]
    webhook_callback_url = f"{base_url}/webhook"

    # Serialize analytics data to JSON string for Chart.js
    analytics_json = json.dumps(data)

    # Calculate cohort statistics for the broadcast console
    count_all = len(users_list)
    count_active = sum(1 for u in users_list if u["phase"] in ("lesson", "quiz", "tutor") and not (u["phase"] == "complete" or u["completed_count"] >= 1))
    count_completed = sum(1 for u in users_list if u["phase"] == "complete" or u["completed_count"] >= 1)
    count_idle = sum(1 for u in users_list if u["phase"] == "idle")

    recipient_options_html = ""
    for u in users_list:
        p = u["phone_number"]
        ph = u["phase"].capitalize()
        pct = u["progress_percent"]
        recipient_options_html += f'<option value="{p}">{p} — {ph} ({pct}% complete)</option>\n'

    # Pre-render table rows
    users_rows_html = ""
    for u in users_list:
        phone = u["phone_number"]
        phase = u["phase"]
        pct = u["progress_percent"]
        mod_title = u["current_module_title"]
        last_seen = u["last_seen_relative"]
        full_last_seen = u["last_seen"]
        messages = u["total_messages"]
        assess_done = "Completed" if len(u.get("assessment_answers") or {}) >= 4 else "Pending"

        # Badge color & text
        if phase == "complete":
            badge_class = "badge-green"
            badge_text = "Graduated"
            row_category = "completed"
        elif phase in ("lesson", "quiz"):
            badge_class = "badge-blue"
            badge_text = f"Learning ({phase.capitalize()})"
            row_category = "active"
        elif phase == "tutor":
            badge_class = "badge-purple"
            badge_text = "AI Tutor"
            row_category = "tutor"
        elif phase == "assessment":
            badge_class = "badge-orange"
            badge_text = "Assessment"
            row_category = "assessment"
        else:
            badge_class = "badge-gray"
            badge_text = "Idle"
            row_category = "idle"

        assess_badge = "badge-green" if assess_done == "Completed" else "badge-gray"
        clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

        users_rows_html += f"""
        <tr data-phone="{phone}" data-category="{row_category}">
            <td class="cell-phone">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-weight:700;color:#0f172a;">{phone}</span>
                    <a href="https://wa.me/{clean_phone}" target="_blank" rel="noopener noreferrer" class="wa-btn" title="Open chat with teacher on WhatsApp">
                        WhatsApp
                    </a>
                </div>
            </td>
            <td><span class="badge {badge_class}"><span class="badge-dot"></span> {badge_text}</span></td>
            <td>
                <div class="progress-wrap">
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width:{pct}%;"></div>
                    </div>
                    <span class="progress-pct">{pct}%</span>
                </div>
                <div class="module-title-sub">{mod_title}</div>
            </td>
            <td class="cell-time" title="{full_last_seen}">{last_seen}</td>
            <td style="text-align:center;font-weight:700;color:#334155;">{messages}</td>
            <td><span class="badge {assess_badge}">{assess_done}</span></td>
            <td class="cell-actions">
                <button class="btn-action btn-view" onclick="openUserModal('{phone}')">Journey</button>
                <button class="btn-action" style="background:#22c55e;color:#ffffff;border:1px solid #16a34a;font-weight:600;" onclick="openDirectMessage('{phone}')" title="Send direct custom message to this educator">Message</button>
                <button class="btn-action btn-reset" onclick="resetUser('{phone}')">Reset</button>
                <button class="btn-action btn-reset" style="color:#ef4444;border-color:#fecaca;" onclick="deleteUser('{phone}')">Delete</button>
            </td>
        </tr>
        """

    # Pre-render activity feed
    activity_items_html = ""
    for act in recent_activity[:15]:
        time_str = db._format_relative_time(act["timestamp"])
        ev = act["event_type"].replace("_", " ").title()
        ph = act["phone_number"]
        det = act.get("details") or ""
        activity_items_html += f"""
        <div class="activity-item">
            <div class="act-dot"></div>
            <div class="act-body">
                <div class="act-header">
                    <span class="act-phone">{ph}</span>
                    <span class="act-time">{time_str}</span>
                </div>
                <div class="act-desc"><b>{ev}</b> — {det}</div>
            </div>
        </div>
        """

    empty_table_state = """
    <tr>
        <td colspan="7" style="text-align:center;padding:48px 24px;">
            <div style="max-width:440px;margin:0 auto;color:#64748b;">
                <h3 style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px;">Waiting for First WhatsApp Learner</h3>
                <p style="font-size:13px;line-height:1.5;margin-bottom:16px;">
                    The system is connected to the database and monitoring incoming messages. Have an educator message <b>"hi"</b> on WhatsApp to enroll.
                </p>
                <span class="badge badge-green"><span class="badge-dot"></span> Live DB Sync Ready</span>
            </div>
        </td>
    </tr>
    """

    empty_activity_state = """
    <div style="text-align:center;padding:32px 16px;color:#94a3b8;font-size:13px;">
        No learning events logged yet.<br>New actions appear here in real-time.
    </div>
    """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EdTech Portal - Admin Intelligence & Analytics</title>
    <link rel="icon" type="image/png" href="/media/logo.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1d4ed8;
            --primary-hover: #1e40af;
            --primary-light: #eff6ff;
            --surface: #ffffff;
            --bg: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --radius-lg: 16px;
            --radius-md: 10px;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.03);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.03);
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            padding-bottom: 60px;
        }}

        /* Top Navigation Bar */
        .top-navbar {{
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            padding: 14px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        }}
        .brand-section {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .brand-logo-img {{
            width: 46px;
            height: 46px;
            border-radius: 50%;
            object-fit: contain;
            box-shadow: 0 4px 10px rgba(29, 78, 216, 0.2);
            border: 1.5px solid #e2e8f0;
            background: #ffffff;
        }}
        .brand-text h1 {{
            font-size: 19px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .brand-text p {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .nav-actions {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .live-status-pill {{
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #065f46;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .pulse-beacon {{
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse-ring 2s infinite;
        }}
        @keyframes pulse-ring {{
            0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
            70% {{ box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
        }}
        .db-badge {{
            background: #f1f5f9;
            border: 1px solid var(--border);
            color: #475569;
            padding: 6px 12px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            font-family: 'JetBrains Mono', monospace;
        }}
        .btn {{
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            border: 1px solid var(--border);
            background: var(--surface);
            color: var(--text-main);
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn:hover {{
            background: #f1f5f9;
            border-color: #cbd5e1;
        }}
        .btn-primary {{
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary);
            box-shadow: 0 2px 6px rgba(29, 78, 216, 0.25);
        }}
        .btn-primary:hover {{
            background: var(--primary-hover);
            border-color: var(--primary-hover);
        }}

        /* Main Container */
        .dashboard-container {{
            max-width: 1440px;
            margin: 28px auto 0;
            padding: 0 32px;
        }}

        /* Hero KPI Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 22px;
            box-shadow: var(--shadow-sm);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
            overflow: hidden;
        }}
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }}
        .stat-top {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        .stat-label {{
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }}
        .stat-icon-wrap {{
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }}
        .stat-val {{
            font-size: 32px;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.8px;
            line-height: 1;
        }}
        .stat-meta {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        /* Charts Layout */
        .charts-row-2col {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 28px;
        }}
        .charts-row-3col {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 28px;
        }}
        @media(max-width: 1024px) {{
            .charts-row-2col, .charts-row-3col {{
                grid-template-columns: 1fr;
            }}
            .dashboard-container {{
                padding: 0 16px;
            }}
            .top-navbar {{
                padding: 14px 16px;
            }}
        }}

        .chart-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            display: flex;
            flex-direction: column;
        }}
        .chart-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .chart-title-wrap {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .chart-card-title {{
            font-size: 16px;
            font-weight: 700;
            color: #0f172a;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .chart-subtitle {{
            font-size: 12px;
            color: var(--text-muted);
            font-weight: normal;
        }}
        .canvas-container {{
            position: relative;
            flex: 1;
            min-height: 240px;
            width: 100%;
        }}

        /* Table & Feed Section */
        .section-split {{
            display: grid;
            grid-template-columns: 2.1fr 1fr;
            gap: 24px;
            margin-bottom: 28px;
        }}
        @media(max-width: 1024px) {{
            .section-split {{
                grid-template-columns: 1fr;
            }}
        }}

        /* Learners Table */
        .table-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
        }}
        .table-toolbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .filter-pills {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}
        .filter-pill {{
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border);
            background: #f8fafc;
            color: #475569;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .filter-pill.active {{
            background: var(--primary);
            color: #ffffff;
            border-color: var(--primary);
        }}
        .search-input {{
            padding: 8px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 13px;
            width: 260px;
            outline: none;
            transition: all 0.2s;
            font-family: inherit;
        }}
        .search-input:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(29, 78, 216, 0.12);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th {{
            background: #f8fafc;
            padding: 12px 14px;
            border-bottom: 2px solid var(--border);
            text-align: left;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}
        tr:hover td {{
            background: #f8fafc;
        }}
        .cell-phone {{
            font-family: 'JetBrains Mono', monospace;
        }}
        .wa-btn {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            background: #dcfce7;
            color: #15803d;
            border: 1px solid #86efac;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-decoration: none;
            transition: all 0.2s;
        }}
        .wa-btn:hover {{
            background: #bbf7d0;
            color: #166534;
        }}
        .progress-wrap {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .progress-bar-bg {{
            background: #e2e8f0;
            border-radius: 6px;
            height: 7px;
            width: 90px;
            overflow: hidden;
        }}
        .progress-bar-fill {{
            background: linear-gradient(90deg, #2563eb, #10b981);
            height: 100%;
            border-radius: 6px;
        }}
        .progress-pct {{
            font-size: 11px;
            font-weight: 700;
            color: #0f172a;
        }}
        .module-title-sub {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 3px;
        }}

        /* Status Badges */
        .badge {{
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }}
        .badge-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}
        .badge-green {{ background: #dcfce7; color: #166534; }}
        .badge-green .badge-dot {{ background: #22c55e; }}
        .badge-blue {{ background: #dbeafe; color: #1e40af; }}
        .badge-blue .badge-dot {{ background: #3b82f6; }}
        .badge-purple {{ background: #f3e8ff; color: #6b21a8; }}
        .badge-purple .badge-dot {{ background: #a855f7; }}
        .badge-orange {{ background: #ffedd5; color: #9a3412; }}
        .badge-orange .badge-dot {{ background: #f97316; }}
        .badge-gray {{ background: #f1f5f9; color: #475569; }}
        .badge-gray .badge-dot {{ background: #94a3b8; }}

        .cell-actions {{
            display: flex;
            gap: 6px;
        }}
        .btn-action {{
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border);
            cursor: pointer;
            background: #ffffff;
            transition: all 0.15s ease;
        }}
        .btn-view {{
            color: var(--primary);
            border-color: #bfdbfe;
        }}
        .btn-view:hover {{
            background: #eff6ff;
        }}
        .btn-reset {{
            color: #dc2626;
            border-color: #fecaca;
        }}
        .btn-reset:hover {{
            background: #fef2f2;
        }}

        /* Live Activity Stream */
        .activity-feed-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            display: flex;
            flex-direction: column;
        }}
        .activity-feed {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 480px;
            overflow-y: auto;
            padding-right: 4px;
        }}
        .activity-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 10px 14px;
            background: #f8fafc;
            border-radius: 10px;
            border: 1px solid #f1f5f9;
            font-size: 12px;
            transition: all 0.15s ease;
        }}
        .activity-item:hover {{
            background: #f1f5f9;
        }}
        .act-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary);
            margin-top: 5px;
            flex-shrink: 0;
        }}
        .act-body {{ flex: 1; }}
        .act-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 3px;
        }}
        .act-phone {{
            font-weight: 700;
            color: #1e293b;
            font-family: 'JetBrains Mono', monospace;
        }}
        .act-time {{
            color: var(--text-muted);
            font-size: 11px;
        }}
        .act-desc {{
            color: #475569;
            line-height: 1.4;
        }}

        /* Survey Intelligence Section */
        .insights-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}
        .insight-card {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 18px;
        }}
        .insight-card h4 {{
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #1e293b;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .insight-row {{
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            padding: 6px 0;
            border-bottom: 1px dashed #e2e8f0;
        }}
        .insight-row:last-child {{
            border-bottom: none;
        }}

        /* User Journey Modal */
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.65);
            backdrop-filter: blur(4px);
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }}
        .modal-content {{
            background: #ffffff;
            border-radius: 20px;
            max-width: 680px;
            width: 100%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .modal-header {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8fafc;
        }}
        .modal-body {{
            padding: 24px;
            overflow-y: auto;
            flex: 1;
        }}
        .close-btn {{
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-muted);
            line-height: 1;
        }}

        /* Spin animation for refresh button */
        .spinning {{
            animation: spin 0.8s linear infinite;
        }}
        @keyframes spin {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        /* Messaging Console Styles */
        .msg-console-body {{
            padding: 24px;
        }}
        .msg-grid-2col {{
            display: grid;
            grid-template-columns: 1.25fr 1fr;
            gap: 24px;
        }}
        @media (max-width: 900px) {{
            .msg-grid-2col {{
                grid-template-columns: 1fr;
            }}
        }}
        .msg-input-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: #475569;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .msg-field {{
            width: 100%;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 13px;
            font-family: inherit;
            color: #0f172a;
            transition: border-color 0.15s ease;
            box-sizing: border-box;
        }}
        .msg-field:focus {{
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
        }}
        .tag-chips-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 8px 0 12px;
        }}
        .tag-chip {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 10px;
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 9999px;
            font-size: 11px;
            font-weight: 600;
            color: #334155;
            cursor: pointer;
            transition: all 0.15s ease;
            user-select: none;
        }}
        .tag-chip:hover {{
            background: #e2e8f0;
            border-color: #94a3b8;
            color: #0f172a;
        }}
        .wa-preview-card {{
            background: #ece5dd;
            background-image: radial-gradient(#d4cbbe 1px, transparent 1px);
            background-size: 16px 16px;
            border: 1px solid #d1d5db;
            border-radius: 14px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            min-height: 200px;
        }}
        .wa-preview-bubble {{
            background: #dcf8c6;
            border-radius: 10px 10px 2px 10px;
            padding: 10px 14px;
            max-width: 100%;
            font-size: 13px;
            line-height: 1.45;
            color: #111827;
            box-shadow: 0 1px 2px rgba(0,0,0,0.12);
            white-space: pre-wrap;
            word-break: break-word;
            align-self: flex-end;
        }}
        .wa-preview-time {{
            font-size: 10px;
            color: #65676b;
            text-align: right;
            margin-top: 4px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 4px;
        }}
        .advisory-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 12px;
            color: #1e40af;
            line-height: 1.5;
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
    <!-- Top Bar -->
    <header class="top-navbar">
        <div class="brand-section">
            <img src="/media/logo.png" alt="EDTECH Logo" class="brand-logo-img" onerror="this.src='/logo.png'">
            <div class="brand-text">
                <h1>
                    <span>EDTECH PORTAL</span>
                    <span style="font-size:11px;font-weight:700;background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:6px;">LIVE CONSOLE</span>
                </h1>
                <p>Teacher Learning Management & Real-Time Analytics</p>
            </div>
        </div>
        <div class="nav-actions">
            <div class="live-status-pill">
                <span class="pulse-beacon"></span>
                <span>Live Database Connected</span>
            </div>
            <div class="db-badge">
                Backend: {backend.upper()} ({db_path})
            </div>
            <button id="refreshBtn" onclick="refreshDashboardData()" class="btn btn-primary" title="Poll and refresh latest data from live database">
                <svg id="refreshIcon" style="width:14px;height:14px;display:inline-block;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                <span>Refresh</span>
            </button>
            <a id="btnExportCsv" href="/admin/export/csv" class="btn" title="Download all learner records as CSV">
                <span>Export CSV</span>
            </a>
            <a href="/admin/logout" class="btn" title="Sign out from dashboard">
                <span>Logout</span>
            </a>
        </div>
    </header>

    <div class="dashboard-container">
        <!-- Ephemeral Storage Guidance Banner (only shown if running SQLite in serverless) -->
        {f'''
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:14px;padding:16px 20px;margin-bottom:24px;display:flex;align-items:flex-start;justify-content:space-between;gap:16px;box-shadow:0 1px 3px rgba(37,99,235,0.06);">
            <div>
                <div style="font-weight:700;color:#1e40af;font-size:14px;margin-bottom:4px;display:flex;align-items:center;gap:6px;">
                    <svg style="width:16px;height:16px;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    <span>Permanent Cloud Storage Recommendation</span>
                </div>
                <div style="color:#1e3a8a;font-size:13px;line-height:1.5;">
                    Vercel serverless containers are ephemeral. To ensure your learner progress, quiz scores, and registrations persist permanently across all container recycles, add free <b>Upstash Redis</b> in your Vercel Project Settings (Environment Variables: <code>UPSTASH_REDIS_REST_URL</code> and <code>UPSTASH_REDIS_REST_TOKEN</code>).
                </div>
            </div>
            <span style="font-size:11px;font-weight:700;background:#dbeafe;color:#1e40af;padding:4px 10px;border-radius:9999px;white-space:nowrap;">SQLite (/tmp)</span>
        </div>
        ''' if data.get('is_ephemeral') else ''}

        <!-- Meta WhatsApp Cloud API Live Health -->
        <div style="background:#ffffff;border:1px solid var(--border);border-radius:16px;padding:20px 24px;margin-bottom:28px;box-shadow:var(--shadow-sm);">
            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <div style="width:42px;height:42px;border-radius:10px;background:#25D366;color:#ffffff;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 10px rgba(37,211,102,0.25);">
                        <svg width="22" height="22" fill="currentColor" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981z"/></svg>
                    </div>
                    <div>
                        <h3 style="font-size:16px;font-weight:700;color:#0f172a;margin:0;">Meta WhatsApp Cloud API Live Health</h3>
                        <p style="font-size:12px;color:#64748b;margin:2px 0 0 0;">Webhook status, credentials & live message tester</p>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                    <span class="badge {token_badge}"><span class="badge-dot"></span> WHATSAPP_TOKEN: {token_text}</span>
                    <span class="badge {phone_badge}"><span class="badge-dot"></span> PHONE_NUMBER_ID: {phone_text}</span>
                    <span class="badge badge-blue"><span class="badge-dot"></span> VERIFY_TOKEN: {verify_token_text}</span>
                </div>
            </div>

            <div style="display:grid;grid-template-columns:1.3fr 1.2fr;gap:20px;background:#f8fafc;padding:16px;border-radius:12px;border:1px solid #f1f5f9;">
                <div>
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#64748b;letter-spacing:0.5px;margin-bottom:6px;">Meta Webhook Callback URL</div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <input id="webhookUrlInput" type="text" readonly value="{webhook_callback_url}" style="flex:1;background:#ffffff;border:1px solid #cbd5e1;padding:8px 12px;border-radius:8px;font-size:12px;font-family:'JetBrains Mono', monospace;color:#0f172a;">
                        <button onclick="copyWebhookUrl()" class="btn" style="padding:8px 14px;font-size:12px;font-weight:600;white-space:nowrap;">Copy URL</button>
                    </div>
                </div>

                <div>
                    <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:#64748b;letter-spacing:0.5px;margin-bottom:6px;">Send WhatsApp Test Ping</div>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <input id="testPhoneInput" type="text" placeholder="Your phone e.g. 15551234567" style="flex:1;background:#ffffff;border:1px solid #cbd5e1;padding:8px 12px;border-radius:8px;font-size:12px;color:#0f172a;">
                        <button id="sendTestBtn" onclick="sendTestWhatsApp()" class="btn btn-primary" style="padding:8px 14px;font-size:12px;font-weight:600;white-space:nowrap;">Test Ping</button>
                    </div>
                </div>
            </div>
            <div id="testPingResult" style="display:none;margin-top:12px;padding:12px 16px;border-radius:10px;font-size:13px;line-height:1.4;"></div>
        </div>

        <!-- Hero KPI Metrics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Total Registered</span>
                    <div class="stat-icon-wrap" style="background:#dbeafe;color:#1d4ed8;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
                    </div>
                </div>
                <div class="stat-val" id="kpiTotalUsers">{summary['total_users']}</div>
                <div class="stat-meta">Unique educators saved in database</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Active Learning</span>
                    <div class="stat-icon-wrap" style="background:#eff6ff;color:#2563eb;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
                    </div>
                </div>
                <div class="stat-val" style="color:#2563eb;" id="kpiActiveUsers">{summary['active_learners']}</div>
                <div class="stat-meta">Engaged in modules and quizzes</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Course Completed</span>
                    <div class="stat-icon-wrap" style="background:#dcfce7;color:#15803d;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5"/></svg>
                    </div>
                </div>
                <div class="stat-val" style="color:#10b981;" id="kpiCompletedUsers">{summary['completed_learners']}</div>
                <div class="stat-meta"><b id="kpiCompletionRate">{summary.get('completion_rate', 0)}%</b> completion rate</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">AI Readiness</span>
                    <div class="stat-icon-wrap" style="background:#f3e8ff;color:#7e22ce;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>
                    </div>
                </div>
                <div class="stat-val" style="color:#8b5cf6;" id="kpiAssessments">{summary['assessment_completed']}</div>
                <div class="stat-meta">Teachers assessed via survey</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Total Interactions</span>
                    <div class="stat-icon-wrap" style="background:#fef3c7;color:#b45309;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                    </div>
                </div>
                <div class="stat-val" style="color:#d97706;" id="kpiInteractions">{summary['total_interactions']}</div>
                <div class="stat-meta">Messages, quizzes, and AI tutor queries</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Peak Study Hour</span>
                    <div class="stat-icon-wrap" style="background:#fee2e2;color:#b91c1c;">
                        <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </div>
                </div>
                <div class="stat-val" style="font-size:24px;padding-top:4px;" id="kpiPeakHour">{summary['peak_hour_utc']}</div>
                <div class="stat-meta">Most active learning window (UTC)</div>
            </div>
        </div>

        <!-- AI Readiness Survey Section -->
        <div class="chart-card" style="margin-bottom: 28px;">
            <div class="chart-card-header">
                <div class="chart-title-wrap">
                    <div>
                        <h2 class="chart-card-title">Teacher AI Readiness Survey Insights</h2>
                        <p class="chart-subtitle">Aggregated self-assessment data from educators</p>
                    </div>
                </div>
            </div>
            <div class="insights-grid" id="surveyInsightsGrid">
                <!-- Injected via JavaScript from real DB data -->
            </div>
        </div>

        <!-- WhatsApp Broadcast & Direct Messaging Console -->
        <div class="chart-card" id="messagingCard" style="margin-bottom: 28px;">
            <div class="chart-card-header" style="flex-wrap:wrap;gap:12px;border-bottom:1px solid var(--border);padding-bottom:16px;">
                <div class="chart-title-wrap">
                    <div style="width:38px;height:38px;border-radius:10px;background:#25D366;color:#ffffff;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 8px rgba(37,211,102,0.3);">
                        <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                    </div>
                    <div>
                        <h2 class="chart-card-title">WhatsApp Broadcast & Direct Messaging</h2>
                        <p class="chart-subtitle">Draft custom messages to specific learners or broadcast announcements to registered cohorts</p>
                    </div>
                </div>
                <div class="filter-pills">
                    <button id="tabBroadcastBtn" class="filter-pill active" onclick="switchMsgTab('broadcast')">Cohort Broadcast</button>
                    <button id="tabDirectBtn" class="filter-pill" onclick="switchMsgTab('direct')">Direct Message to Individual</button>
                </div>
            </div>

            <div class="msg-console-body">
                <!-- TAB 1: COHORT BROADCAST -->
                <div id="broadcastTab">
                    <div class="msg-grid-2col">
                        <div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">
                                <div>
                                    <div class="msg-input-label">
                                        <span>Target Cohort</span>
                                    </div>
                                    <select id="broadcastSegment" class="msg-field" onchange="onSegmentChange()">
                                        <option value="all">All Registered Teachers ({count_all})</option>
                                        <option value="active">Active Learners in Module 1 ({count_active})</option>
                                        <option value="completed">Graduated / Finished ({count_completed})</option>
                                        <option value="idle">Idle / Not Started ({count_idle})</option>
                                    </select>
                                </div>
                                <div>
                                    <div class="msg-input-label">
                                        <span>Quick Draft Preset</span>
                                    </div>
                                    <select id="broadcastTemplate" class="msg-field" onchange="applyBroadcastTemplate(this.value)">
                                        <option value="">-- Choose Draft Template --</option>
                                        <option value="nudge">Course Nudge: Continue Module 1</option>
                                        <option value="congrats">Congratulations: Module 1 Complete</option>
                                        <option value="resources">New AI Pedagogical Resources</option>
                                        <option value="checkin">Pedagogical Practice Check-in</option>
                                    </select>
                                </div>
                            </div>

                            <div class="msg-input-label">
                                <span>Message Content</span>
                                <span style="font-size:11px;color:var(--text-muted);font-weight:normal;" id="broadcastCharCount">0 characters</span>
                            </div>
                            <textarea id="broadcastMessageText" class="msg-field" rows="5" placeholder="Draft your broadcast message to educators here..." oninput="updateBroadcastPreview()"></textarea>

                            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:6px;">
                                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                                    <span style="font-size:11px;font-weight:700;color:#64748b;">Insert tags:</span>
                                    <span class="tag-chip" onclick="insertTag('{{phone}}', 'broadcastMessageText', updateBroadcastPreview)">+ {{phone}}</span>
                                    <span class="tag-chip" onclick="insertTag('{{status}}', 'broadcastMessageText', updateBroadcastPreview)">+ {{status}}</span>
                                    <span class="tag-chip" onclick="insertTag('{{progress}}', 'broadcastMessageText', updateBroadcastPreview)">+ {{progress}}</span>
                                </div>
                                <button id="btnSendBroadcast" onclick="sendBroadcast()" class="btn btn-primary" style="background:#25D366;border-color:#22c55e;padding:9px 18px;font-weight:700;">
                                    Send Broadcast
                                </button>
                            </div>

                            <div id="broadcastResult" style="display:none;margin-top:14px;padding:12px 16px;border-radius:10px;font-size:13px;line-height:1.4;"></div>
                        </div>

                        <div>
                            <div class="msg-input-label">
                                <span>Simulated WhatsApp Live Preview</span>
                                <span style="font-size:11px;color:#10b981;font-weight:600;" id="broadcastPreviewBadge">Batch send</span>
                            </div>
                            <div class="wa-preview-card">
                                <div class="wa-preview-bubble" id="broadcastPreviewBubble">
                                    Your message will preview here in real-time as you draft...
                                    <div class="wa-preview-time">
                                        <span>12:00</span>
                                        <svg width="12" height="12" fill="none" stroke="#53bdeb" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7m-5 0l4 4"/></svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TAB 2: DIRECT MESSAGE -->
                <div id="directTab" style="display:none;">
                    <div class="msg-grid-2col">
                        <div>
                            <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:14px;margin-bottom:14px;">
                                <div>
                                    <div class="msg-input-label">
                                        <span>Select Registered Educator</span>
                                    </div>
                                    <select id="directRecipientSelect" class="msg-field" onchange="onDirectRecipientSelect(this.value)">
                                        <option value="">-- Choose Educator from DB --</option>
                                        {recipient_options_html}
                                    </select>
                                </div>
                                <div>
                                    <div class="msg-input-label">
                                        <span>Or Direct Phone Input</span>
                                    </div>
                                    <input id="directPhoneInput" type="text" class="msg-field" placeholder="e.g. 251911223344" oninput="updateDirectPreview()">
                                </div>
                            </div>

                            <div style="margin-bottom:14px;">
                                <div class="msg-input-label">
                                    <span>Quick Draft Preset</span>
                                </div>
                                <select id="directTemplate" class="msg-field" onchange="applyDirectTemplate(this.value)">
                                    <option value="">-- Choose Draft Template --</option>
                                    <option value="support">Direct Support: Pedagogical Assistance</option>
                                    <option value="followup">Learning Follow-up: Check-in on Progress</option>
                                    <option value="quiz_help">Quiz Support: Module 1 Questions</option>
                                </select>
                            </div>

                            <div class="msg-input-label">
                                <span>Message Content</span>
                                <span style="font-size:11px;color:var(--text-muted);font-weight:normal;" id="directCharCount">0 characters</span>
                            </div>
                            <textarea id="directMessageText" class="msg-field" rows="5" placeholder="Draft your custom message to this specific teacher here..." oninput="updateDirectPreview()"></textarea>

                            <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-top:6px;">
                                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                                    <span style="font-size:11px;font-weight:700;color:#64748b;">Insert tags:</span>
                                    <span class="tag-chip" onclick="insertTag('{{phone}}', 'directMessageText', updateDirectPreview)">+ {{phone}}</span>
                                    <span class="tag-chip" onclick="insertTag('{{status}}', 'directMessageText', updateDirectPreview)">+ {{status}}</span>
                                    <span class="tag-chip" onclick="insertTag('{{progress}}', 'directMessageText', updateDirectPreview)">+ {{progress}}</span>
                                </div>
                                <button id="btnSendDirect" onclick="sendDirectMessage()" class="btn btn-primary" style="background:#25D366;border-color:#22c55e;padding:9px 18px;font-weight:700;">
                                    Send Direct Message
                                </button>
                            </div>

                            <div id="directResult" style="display:none;margin-top:14px;padding:12px 16px;border-radius:10px;font-size:13px;line-height:1.4;"></div>
                        </div>

                        <div>
                            <div class="msg-input-label">
                                <span>Simulated WhatsApp Live Preview</span>
                                <span style="font-size:11px;color:#2563eb;font-weight:600;" id="directPreviewBadge">Direct message</span>
                            </div>
                            <div class="wa-preview-card">
                                <div class="wa-preview-bubble" id="directPreviewBubble">
                                    Your message will preview here in real-time as you draft...
                                    <div class="wa-preview-time">
                                        <span>12:00</span>
                                        <svg width="12" height="12" fill="none" stroke="#53bdeb" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7m-5 0l4 4"/></svg>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Learners Table & Live Activity Feed -->
        <div class="section-split">
            <!-- Learners Data Table -->
            <div class="table-card">
                <div class="table-toolbar">
                    <div>
                        <h2 style="font-size:16px;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:8px;">
                            <span>Learner Registry (<span id="tableCount">{len(users_list)}</span>)</span>
                        </h2>
                        <p style="font-size:12px;color:var(--text-muted);margin-top:2px;">All educators registered through WhatsApp</p>
                    </div>
                    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                        <input type="text" id="userSearch" class="search-input" placeholder="Search phone number..." oninput="filterTable()">
                        <div class="filter-pills" id="tableFilterPills">
                            <button class="filter-pill active" onclick="setFilter('all', this)">All</button>
                            <button class="filter-pill" onclick="setFilter('active', this)">Active</button>
                            <button class="filter-pill" onclick="setFilter('completed', this)">Graduated</button>
                            <button class="filter-pill" onclick="setFilter('tutor', this)">AI Tutor</button>
                            <button class="filter-pill" onclick="setFilter('idle', this)">Idle</button>
                        </div>
                    </div>
                </div>
                <div style="overflow-x:auto;">
                    <table id="learnersTable">
                        <thead>
                            <tr>
                                <th>Phone (WhatsApp)</th>
                                <th>Status</th>
                                <th>Module Progress</th>
                                <th>Last Active</th>
                                <th style="text-align:center;">Msgs</th>
                                <th>Survey</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="learnersTableBody">
                            {users_rows_html if users_rows_html else empty_table_state}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Live Activity Feed -->
            <div class="activity-feed-card">
                <div class="chart-card-header" style="margin-bottom:14px;">
                    <div class="chart-title-wrap">
                        <h2 class="chart-card-title">Live Activity Stream</h2>
                    </div>
                    <span style="font-size:11px;color:var(--text-muted);font-weight:600;">Real-Time</span>
                </div>
                <div class="activity-feed" id="activityFeed">
                    {activity_items_html if activity_items_html else empty_activity_state}
                </div>
            </div>
        </div>
    </div>

    <!-- Student Journey Modal -->
    <div id="userModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div style="display:flex;align-items:center;gap:10px;">
                    <img src="/media/logo.png" alt="Logo" style="width:32px;height:32px;border-radius:50%;" onerror="this.src='/logo.png'">
                    <h3 id="modalTitle" style="font-size:16px;font-weight:700;">Learner Journey</h3>
                </div>
                <button class="close-btn" onclick="closeUserModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody">
                <p>Loading journey details from live database...</p>
            </div>
        </div>
    </div>

    <!-- Initial Data Payload from Server -->
    <script id="initialData" type="application/json">
        {analytics_json}
    </script>

    <script>
        let currentFilter = 'all';

        // Load initial data from server
        let dashboardData = JSON.parse(document.getElementById('initialData').textContent);

        document.addEventListener('DOMContentLoaded', () => {{
            renderSurveyCards(dashboardData.assessment_insights);

            // Ensure CSV export link carries current password parameter if present in URL
            const urlParams = new URLSearchParams(window.location.search);
            const adminPass = urlParams.get('password') || urlParams.get('pass');
            const exportBtn = document.getElementById('btnExportCsv');
            if (exportBtn && adminPass) {{
                exportBtn.href = `/admin/export/csv?password=${{encodeURIComponent(adminPass)}}`;
            }}

            // Auto-sync polling every 30 seconds
            setInterval(() => {{
                refreshDashboardData(true);
            }}, 30000);
        }});

        function renderSurveyCards(insights) {{
            const grid = document.getElementById('surveyInsightsGrid');
            if (!insights) return;

            const q1 = insights.q1_ai_use || insights.ai_use || {{}};
            const q2 = insights.q2_comfort || insights.comfort || {{}};
            const q3 = insights.q3_challenge || insights.challenge || {{}};
            const q4 = insights.q4_goal || insights.goal || {{}};

            grid.innerHTML = `
                <div class="insight-card">
                    <h4>AI Usage Frequency</h4>
                    <div class="insight-row"><span>Never:</span><b>${{q1.A || q1['Never'] || 0}}</b></div>
                    <div class="insight-row"><span>Sometimes:</span><b>${{q1.B || q1['Sometimes'] || 0}}</b></div>
                    <div class="insight-row"><span>Regularly:</span><b>${{q1.C || q1['Regularly'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4>Confidence Level</h4>
                    <div class="insight-row"><span>Not confident:</span><b>${{q2.A || q2['Not confident'] || 0}}</b></div>
                    <div class="insight-row"><span>Somewhat confident:</span><b>${{q2.B || q2['Somewhat confident'] || 0}}</b></div>
                    <div class="insight-row"><span>Very confident:</span><b>${{q2.C || q2['Very confident'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4>Primary Classroom Challenge</h4>
                    <div class="insight-row"><span>Large Class Sizes (50+):</span><b>${{q3.A || q3['Large classes'] || 0}}</b></div>
                    <div class="insight-row"><span>Limited Devices/Internet:</span><b>${{q3.B || q3['Limited devices'] || 0}}</b></div>
                    <div class="insight-row"><span>Writing Effective Prompts:</span><b>${{q3.C || q3['Prompt writing'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4>Primary Course Goal</h4>
                    <div class="insight-row"><span>Practical Classroom Ideas:</span><b>${{q4.A || q4['Practical ideas'] || 0}}</b></div>
                    <div class="insight-row"><span>Time-Saving Planning Tools:</span><b>${{q4.B || q4['Time saving'] || 0}}</b></div>
                    <div class="insight-row"><span>Responsible & Ethical AI:</span><b>${{q4.C || q4['Ethical AI'] || 0}}</b></div>
                </div>
            `;
        }}

        function adminApiUrl(path) {{
            const urlParams = new URLSearchParams(window.location.search);
            const adminPass = urlParams.get('password') || urlParams.get('pass');
            if (!adminPass) return path;
            const sep = path.includes('?') ? '&' : '?';
            return `${{path}}${{sep}}password=${{encodeURIComponent(adminPass)}}`;
        }}

        async function refreshDashboardData(silent = false) {{
            const btn = document.getElementById('refreshBtn');
            const icon = document.getElementById('refreshIcon');
            if (!silent && icon) icon.classList.add('spinning');

            try {{
                const resp = await fetch(adminApiUrl('/admin/api/analytics'));
                if (!resp.ok) throw new Error('Network error');
                const data = await resp.json();
                dashboardData = data;

                // Update KPIs
                const sum = data.summary;
                document.getElementById('kpiTotalUsers').innerText = sum.total_users;
                document.getElementById('kpiActiveUsers').innerText = sum.active_learners;
                document.getElementById('kpiCompletedUsers').innerText = sum.completed_learners;
                document.getElementById('kpiCompletionRate').innerText = (sum.completion_rate || 0) + '%';
                document.getElementById('kpiAssessments').innerText = sum.assessment_completed;
                document.getElementById('kpiInteractions').innerText = sum.total_interactions;
                document.getElementById('kpiPeakHour').innerText = sum.peak_hour_utc;
                document.getElementById('tableCount').innerText = data.users.length;

                // Update Survey Insights
                renderSurveyCards(data.assessment_insights || data.survey_insights);

                // Re-render Table & Messaging Audience Selectors
                renderTableRows(data.users);
                updateMessagingAudienceUI(data.users);

                // Re-render Activity Stream
                renderActivityFeed(data.recent_activity);

            }} catch (err) {{
                console.error('Refresh error:', err);
            }} finally {{
                if (icon) icon.classList.remove('spinning');
            }}
        }}

        function copyWebhookUrl() {{
            const input = document.getElementById('webhookUrlInput');
            if (input) {{
                input.select();
                navigator.clipboard.writeText(input.value);
                alert('Webhook URL copied to clipboard!\\n\\nPaste this into Meta Developer Portal > WhatsApp > Configuration > Callback URL');
            }}
        }}

        async function sendTestWhatsApp() {{
            const phoneInput = document.getElementById('testPhoneInput');
            const resDiv = document.getElementById('testPingResult');
            const btn = document.getElementById('sendTestBtn');
            const phone = phoneInput ? phoneInput.value.trim() : '';

            if (!phone) {{
                alert('Please enter your WhatsApp phone number with country code (e.g. 15551234567)');
                return;
            }}

            btn.disabled = true;
            btn.innerText = 'Sending...';
            resDiv.style.display = 'block';
            resDiv.style.background = '#eff6ff';
            resDiv.style.color = '#1e40af';
            resDiv.innerHTML = 'Connecting to Meta WhatsApp Cloud API...';

            try {{
                const resp = await fetch(adminApiUrl('/admin/api/test-whatsapp'), {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{phone: phone}})
                }});
                const data = await resp.json();
                if (data.success) {{
                    resDiv.style.background = '#dcfce7';
                    resDiv.style.color = '#166534';
                    resDiv.innerHTML = '<b>Success:</b> Test ping sent to WhatsApp (' + phone + '). Check your phone!';
                }} else {{
                    resDiv.style.background = '#fee2e2';
                    resDiv.style.color = '#991b1b';
                    resDiv.innerHTML = '<b>Meta API Error:</b> ' + (data.error || 'Failed to send') +
                        (data.hint ? '<br><span style="font-size:12px;margin-top:6px;display:inline-block;color:#7f1d1d;"><b>Action required:</b> ' + data.hint + '</span>' : '');
                }}
            }} catch (err) {{
                resDiv.style.background = '#fee2e2';
                resDiv.style.color = '#991b1b';
                resDiv.innerHTML = '<b>Network Error:</b> ' + err.message;
            }} finally {{
                btn.disabled = false;
                btn.innerText = 'Test Ping';
            }}
        }}

        function renderTableRows(users) {{
            const tbody = document.getElementById('learnersTableBody');
            if (!users || users.length === 0) {{
                tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:48px 24px;">
                        <div style="max-width:440px;margin:0 auto;color:#64748b;">
                            <h3 style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px;">Waiting for First WhatsApp Learner</h3>
                            <p style="font-size:13px;line-height:1.5;">The system is live and recording. Have a teacher message the bot on WhatsApp to see live metrics.</p>
                        </div>
                    </td>
                </tr>`;
                return;
            }}

            let html = '';
            users.forEach(u => {{
                const phone = u.phone_number;
                const safePhone = escapeHtml(phone);
                const phase = u.phase;
                const pct = u.progress_percent;
                const mod_title = escapeHtml(u.current_module_title || '');
                const last_seen = escapeHtml(u.last_seen_relative || '');
                const messages = u.total_messages;
                const assess_done = (u.assessment_answers && Object.keys(u.assessment_answers).length >= 4) ? 'Completed' : 'Pending';

                let badge_class = 'badge-gray';
                let badge_text = 'Idle';
                let row_category = 'idle';

                if (phase === 'complete') {{
                    badge_class = 'badge-green';
                    badge_text = 'Graduated';
                    row_category = 'completed';
                }} else if (phase === 'lesson' || phase === 'quiz') {{
                    badge_class = 'badge-blue';
                    badge_text = `Learning (${{phase.toUpperCase()}})`;
                    row_category = 'active';
                }} else if (phase === 'tutor') {{
                    badge_class = 'badge-purple';
                    badge_text = 'AI Tutor';
                    row_category = 'tutor';
                }} else if (phase === 'assessment') {{
                    badge_class = 'badge-orange';
                    badge_text = 'Assessment';
                    row_category = 'assessment';
                }}

                const assess_badge = assess_done === 'Completed' ? 'badge-green' : 'badge-gray';
                const clean_phone = phone.replace('+', '').replace(/\\s/g, '').replace(/-/g, '');

                html += `
                <tr data-phone="${{safePhone}}" data-category="${{row_category}}">
                    <td class="cell-phone">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-weight:700;color:#0f172a;">${{safePhone}}</span>
                            <a href="https://wa.me/${{clean_phone}}" target="_blank" rel="noopener noreferrer" class="wa-btn" title="Open chat with teacher on WhatsApp">
                                WhatsApp
                            </a>
                        </div>
                    </td>
                    <td><span class="badge ${{badge_class}}"><span class="badge-dot"></span> ${{badge_text}}</span></td>
                    <td>
                        <div class="progress-wrap">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width:${{pct}}%;"></div>
                            </div>
                            <span class="progress-pct">${{pct}}%</span>
                        </div>
                        <div class="module-title-sub">${{mod_title}}</div>
                    </td>
                    <td class="cell-time">${{last_seen}}</td>
                    <td style="text-align:center;font-weight:700;color:#334155;">${{messages}}</td>
                    <td><span class="badge ${{assess_badge}}">${{assess_done}}</span></td>
                    <td class="cell-actions">
                        <button class="btn-action btn-view" onclick="openUserModal('${{safePhone}}')">Journey</button>
                        <button class="btn-action" style="background:#22c55e;color:#ffffff;border:1px solid #16a34a;font-weight:600;" onclick="openDirectMessage('${{safePhone}}')" title="Send direct custom message to this educator">Message</button>
                        <button class="btn-action btn-reset" onclick="resetUser('${{safePhone}}')">Reset</button>
                        <button class="btn-action btn-reset" style="color:#ef4444;border-color:#fecaca;" onclick="deleteUser('${{safePhone}}')">Delete</button>
                    </td>
                </tr>`;
            }});
            tbody.innerHTML = html;
            filterTable();
        }}

        function updateMessagingAudienceUI(users) {{
            if (!users) return;
            const segSelect = document.getElementById('broadcastSegment');
            if (segSelect) {{
                const curSeg = segSelect.value;
                const total = users.length;
                const completed = users.filter(u => u.phase === 'complete' || (u.completed_count || 0) >= 1).length;
                const active = users.filter(u => (u.phase === 'lesson' || u.phase === 'quiz' || u.phase === 'tutor') && u.phase !== 'complete' && (u.completed_count || 0) < 1).length;
                const idle = users.filter(u => u.phase === 'idle').length;
                segSelect.innerHTML = `
                    <option value="all">All Registered Teachers (${{total}})</option>
                    <option value="active">Active Learners in Module 1 (${{active}})</option>
                    <option value="completed">Graduated / Finished (${{completed}})</option>
                    <option value="idle">Idle / Not Started (${{idle}})</option>
                `;
                segSelect.value = curSeg || 'all';
            }}

            const recSelect = document.getElementById('directRecipientSelect');
            if (recSelect) {{
                const curPhone = recSelect.value;
                let opts = '<option value="">-- Choose Educator from DB --</option>';
                users.forEach(u => {{
                    const p = escapeHtml(u.phone_number);
                    const ph = escapeHtml((u.phase || 'idle').charAt(0).toUpperCase() + (u.phase || 'idle').slice(1));
                    opts += `<option value="${{p}}">${{p}} — ${{ph}} (${{u.progress_percent || 0}}% complete)</option>`;
                }});
                recSelect.innerHTML = opts;
                if (curPhone) recSelect.value = curPhone;
            }}
        }}

        function renderActivityFeed(activities) {{
            const feed = document.getElementById('activityFeed');
            if (!activities || activities.length === 0) {{
                feed.innerHTML = '<div style="text-align:center;padding:32px 16px;color:#94a3b8;font-size:13px;">No events logged yet.</div>';
                return;
            }}

            let html = '';
            activities.slice(0, 20).forEach(act => {{
                const ev = act.event_type.replace(/_/g, ' ').toUpperCase();
                html += `
                <div class="activity-item">
                    <div class="act-dot"></div>
                    <div class="act-body">
                        <div class="act-header">
                            <span class="act-phone">${{act.phone_number}}</span>
                            <span class="act-time">Just now</span>
                        </div>
                        <div class="act-desc"><b>${{ev}}</b> — ${{act.details || ''}}</div>
                    </div>
                </div>`;
            }});
            feed.innerHTML = html;
        }}

        function setFilter(cat, btn) {{
            currentFilter = cat;
            document.querySelectorAll('#tableFilterPills .filter-pill').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            filterTable();
        }}

        function filterTable() {{
            const query = document.getElementById('userSearch').value.toLowerCase();
            const rows = document.querySelectorAll('#learnersTable tbody tr');
            rows.forEach(row => {{
                const phone = (row.getAttribute('data-phone') || '').toLowerCase();
                const category = row.getAttribute('data-category') || '';
                const matchSearch = phone.includes(query);
                const matchCat = currentFilter === 'all' || category === currentFilter;
                row.style.display = (matchSearch && matchCat) ? '' : 'none';
            }});
        }}

        async function openUserModal(phone) {{
            const modal = document.getElementById('userModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');
            modalTitle.innerText = 'Learner Journey: ' + phone;
            modal.style.display = 'flex';
            modalBody.innerHTML = '<p style="color:#64748b;">Loading full timeline from database...</p>';

            try {{
                const resp = await fetch(adminApiUrl('/admin/api/user/' + encodeURIComponent(phone)));
                if (!resp.ok) throw new Error('User record not found');
                const data = await resp.json();
                const u = data.user;
                const hist = data.history;

                let histHtml = '';
                if (hist && hist.length > 0) {{
                    hist.forEach(item => {{
                        histHtml += `
                        <div style="padding:10px 14px;border-left:3px solid #2563eb;background:#f8fafc;margin-bottom:8px;border-radius:0 10px 10px 0;">
                            <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;">
                                <b>${{item.event_type.replace(/_/g, ' ').toUpperCase()}}</b>
                                <span>${{new Date(item.timestamp).toLocaleString()}}</span>
                            </div>
                            <div style="font-size:13px;margin-top:4px;color:#1e293b;">${{item.details || 'Message received'}}</div>
                        </div>`;
                    }});
                }} else {{
                    histHtml = '<p style="color:#94a3b8;font-size:13px;">No timeline entries recorded yet.</p>';
                }}

                modalBody.innerHTML = `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px;background:#f1f5f9;padding:16px;border-radius:12px;font-size:13px;">
                        <div><b>Phone:</b> <span style="font-family:monospace;">${{u.phone_number}}</span></div>
                        <div><b>Status:</b> ${{u.phase.toUpperCase()}}</div>
                        <div><b>Current Step:</b> ${{u.phase === 'complete' ? 'Course Completed' : (u.lesson_index !== null ? 'Module ' + (u.lesson_index + 1) : 'None')}}</div>
                        <div><b>Total Interactions:</b> ${{u.total_messages || 0}} msgs</div>
                        <div><b>Completed Modules:</b> ${{(u.completed_lessons || []).length}} / ${{data.progression_funnel ? data.progression_funnel.total_modules : 1}}</div>
                        <div><b>Last Active:</b> ${{u.last_seen ? new Date(u.last_seen).toLocaleString() : 'Never'}}</div>
                    </div>
                    <h4 style="font-size:14px;margin-bottom:12px;font-weight:700;">Chronological Learning Log (${{hist.length}} actions)</h4>
                    <div style="max-height:340px;overflow-y:auto;">${{histHtml}}</div>
                `;
            }} catch (err) {{
                modalBody.innerHTML = `<p style="color:#ef4444;">Error loading student details: ${{err.message}}</p>`;
            }}
        }}

        function closeUserModal() {{
            document.getElementById('userModal').style.display = 'none';
        }}

        async function resetUser(phone) {{
            if (!confirm(`Are you sure you want to reset all course progress for ${{phone}}?`)) return;
            try {{
                const resp = await fetch(adminApiUrl('/admin/api/user/' + encodeURIComponent(phone) + '/reset'), {{ method: 'POST' }});
                if (resp.ok) {{
                    refreshDashboardData();
                }} else {{
                    alert('Failed to reset student.');
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        async function deleteUser(phone) {{
            if (!confirm(`Are you sure you want to permanently delete learner ${{phone}} from the database?`)) return;
            try {{
                const resp = await fetch(adminApiUrl('/admin/api/user/' + encodeURIComponent(phone) + '/delete'), {{ method: 'POST' }});
                if (resp.ok) {{
                    refreshDashboardData();
                }} else {{
                    alert('Failed to delete student.');
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        const BROADCAST_TEMPLATES = {{
            nudge: "Hello Teacher! A quick friendly reminder from EdTech Hub: your introductory course on Artificial Intelligence for Ethiopian Teachers is in progress. Whenever you have 5 minutes, reply 'continue' or 'menu' to pick up right where you left off!",
            congrats: "Congratulations, Teacher! You have completed Module 1 of Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia. Remember: AI is your assistant and you are the editor. Text us anytime to consult your AI Tutor or review the concepts!",
            resources: "Greetings from EdTech Hub! New instructional prompts, offline classroom examples, and pedagogical strategies have been updated. Text 'menu' anytime to explore the latest materials.",
            checkin: "Hello! How is your teaching practice going this week? Have you had a chance to try drafting a lesson plan or quiz with AI? If you have any questions or ideas, our AI Tutor is ready to assist you here 24/7."
        }};

        const DIRECT_TEMPLATES = {{
            support: "Hello Teacher! We noticed you are currently learning with EdTech Hub. Is there any question about Module 1 or classroom AI integration that we can assist you with today? Feel free to reply directly to this message.",
            followup: "Hello! Following up on your progress in AI for Teaching and Learning. Great work on your learning journey so far! How are you finding the course materials? Let us know if you need any support.",
            quiz_help: "Hello Teacher! We saw you were working on the Module 1 quiz. If any concept needs clarification, our AI Tutor is always here to guide you. Feel free to ask any question or reply 'menu' to continue."
        }};

        function switchMsgTab(tab) {{
            const bTab = document.getElementById('broadcastTab');
            const dTab = document.getElementById('directTab');
            const bBtn = document.getElementById('tabBroadcastBtn');
            const dBtn = document.getElementById('tabDirectBtn');
            if (tab === 'broadcast') {{
                bTab.style.display = 'block';
                dTab.style.display = 'none';
                bBtn.classList.add('active');
                dBtn.classList.remove('active');
            }} else {{
                bTab.style.display = 'none';
                dTab.style.display = 'block';
                bBtn.classList.remove('active');
                dBtn.classList.add('active');
            }}
        }}

        function applyBroadcastTemplate(key) {{
            const txt = document.getElementById('broadcastMessageText');
            if (key && BROADCAST_TEMPLATES[key]) {{
                txt.value = BROADCAST_TEMPLATES[key];
            }}
            updateBroadcastPreview();
        }}

        function applyDirectTemplate(key) {{
            const txt = document.getElementById('directMessageText');
            if (key && DIRECT_TEMPLATES[key]) {{
                txt.value = DIRECT_TEMPLATES[key];
            }}
            updateDirectPreview();
        }}

        function insertTag(tag, textareaId, callback) {{
            const el = document.getElementById(textareaId);
            if (!el) return;
            const start = (el.selectionStart !== undefined && el.selectionStart !== null) ? el.selectionStart : el.value.length;
            const end = (el.selectionEnd !== undefined && el.selectionEnd !== null) ? el.selectionEnd : el.value.length;
            el.value = el.value.substring(0, start) + tag + el.value.substring(end);
            el.selectionStart = el.selectionEnd = start + tag.length;
            el.focus();
            if (callback) callback();
        }}

        function updateBroadcastPreview() {{
            const txt = document.getElementById('broadcastMessageText').value;
            const bubble = document.getElementById('broadcastPreviewBubble');
            const counter = document.getElementById('broadcastCharCount');
            counter.textContent = `${{txt.length}} characters`;
            const now = new Date();
            const timeStr = now.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});
            
            const rendered = (txt || "Your message will preview here in real-time as you draft...")
                .split('{{phone}}').join("+251911223344")
                .split('{{status}}').join("Learning")
                .split('{{progress}}').join("50%");
            
            bubble.innerHTML = `${{escapeHtml(rendered)}}<div class="wa-preview-time"><span>${{timeStr}}</span><svg width="12" height="12" fill="none" stroke="#53bdeb" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7m-5 0l4 4"/></svg></div>`;
        }}

        function updateDirectPreview() {{
            const txt = document.getElementById('directMessageText').value;
            const phone = document.getElementById('directPhoneInput').value.trim() || "+251911223344";
            const bubble = document.getElementById('directPreviewBubble');
            const counter = document.getElementById('directCharCount');
            counter.textContent = `${{txt.length}} characters`;
            const now = new Date();
            const timeStr = now.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});
            
            const rendered = (txt || "Your message will preview here in real-time as you draft...")
                .split('{{phone}}').join(phone)
                .split('{{status}}').join("Learning")
                .split('{{progress}}').join("50%");
            
            bubble.innerHTML = `${{escapeHtml(rendered)}}<div class="wa-preview-time"><span>${{timeStr}}</span><svg width="12" height="12" fill="none" stroke="#53bdeb" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7m-5 0l4 4"/></svg></div>`;
        }}

        function onDirectRecipientSelect(val) {{
            if (val) {{
                document.getElementById('directPhoneInput').value = val;
            }}
            updateDirectPreview();
        }}

        function onSegmentChange() {{
            const seg = document.getElementById('broadcastSegment').value;
            const badge = document.getElementById('broadcastPreviewBadge');
            badge.textContent = `Batch to ${{seg}}`;
        }}

        function openDirectMessage(phone) {{
            switchMsgTab('direct');
            const phoneInput = document.getElementById('directPhoneInput');
            const select = document.getElementById('directRecipientSelect');
            if (phoneInput) phoneInput.value = phone;
            if (select) {{
                let matched = false;
                for (let i = 0; i < select.options.length; i++) {{
                    if (select.options[i].value === phone) {{
                        select.selectedIndex = i;
                        matched = true;
                        break;
                    }}
                }}
                if (!matched) select.selectedIndex = 0;
            }}
            updateDirectPreview();
            const card = document.getElementById('messagingCard');
            if (card) {{
                card.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
            const txt = document.getElementById('directMessageText');
            if (txt) {{
                try {{ txt.focus({{ preventScroll: true }}); }} catch (_) {{ txt.focus(); }}
            }}
        }}

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        async function sendBroadcast() {{
            const segment = document.getElementById('broadcastSegment').value;
            const message = document.getElementById('broadcastMessageText').value.trim();
            const resultDiv = document.getElementById('broadcastResult');
            const btn = document.getElementById('btnSendBroadcast');
            
            if (!message) {{
                alert('Please enter a broadcast message to send.');
                return;
            }}
            if (!confirm(`Are you sure you want to broadcast this message to the '${{segment.toUpperCase()}}' cohort?`)) {{
                return;
            }}
            
            btn.disabled = true;
            btn.innerHTML = '<span class="spinning" style="display:inline-block;margin-right:6px;">↻</span> Broadcasting...';
            resultDiv.style.display = 'none';
            
            try {{
                const resp = await fetch(adminApiUrl('/admin/api/broadcast'), {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ segment, message }})
                }});
                const res = await resp.json();
                
                resultDiv.style.display = 'block';
                if (res.success) {{
                    const failures = (res.results || []).filter(r => r.status !== 'sent');
                    if (res.sent_count > 0) {{
                        resultDiv.style.background = '#dcfce7';
                        resultDiv.style.border = '1px solid #86efac';
                        resultDiv.style.color = '#15803d';
                    }} else {{
                        resultDiv.style.background = '#fee2e2';
                        resultDiv.style.border = '1px solid #fca5a5';
                        resultDiv.style.color = '#b91c1c';
                    }}
                    let failHtml = '';
                    if (failures.length > 0) {{
                        const items = failures.slice(0, 5).map(f => `<li>${{escapeHtml(f.phone)}}: ${{escapeHtml(f.error || 'Failed')}}</li>`).join('');
                        failHtml = `<ul style="margin:6px 0 0 18px;font-size:12px;color:#b91c1c;">${{items}}</ul>`;
                    }}
                    resultDiv.innerHTML = `<b>Broadcast Finished!</b> Delivered to <b>${{res.sent_count}} / ${{res.total_targets}}</b> teachers successfully.` +
                        (res.failed_count > 0 ? ` <span style="color:#b91c1c;">(${{res.failed_count}} failed)</span>${{failHtml}}` : '');
                    refreshDashboardData(true);
                }} else {{
                    resultDiv.style.background = '#fee2e2';
                    resultDiv.style.border = '1px solid #fca5a5';
                    resultDiv.style.color = '#b91c1c';
                    resultDiv.innerHTML = `<b>Broadcast Error:</b> ${{escapeHtml(res.error || 'Failed to send broadcast')}}`;
                }}
            }} catch (e) {{
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#fee2e2';
                resultDiv.style.border = '1px solid #fca5a5';
                resultDiv.style.color = '#b91c1c';
                resultDiv.innerHTML = `<b>Error:</b> ${{escapeHtml(e.message)}}`;
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = 'Send Broadcast';
            }}
        }}

        async function sendDirectMessage() {{
            const phone = document.getElementById('directPhoneInput').value.trim();
            const message = document.getElementById('directMessageText').value.trim();
            const resultDiv = document.getElementById('directResult');
            const btn = document.getElementById('btnSendDirect');
            
            if (!phone) {{
                alert('Please select or enter a recipient phone number.');
                return;
            }}
            if (!message) {{
                alert('Please enter a message to send.');
                return;
            }}
            
            btn.disabled = true;
            btn.innerHTML = '<span class="spinning" style="display:inline-block;margin-right:6px;">↻</span> Sending...';
            resultDiv.style.display = 'none';
            
            try {{
                const resp = await fetch(adminApiUrl('/admin/api/direct-message'), {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ phone, message }})
                }});
                const res = await resp.json();
                
                resultDiv.style.display = 'block';
                if (res.success) {{
                    resultDiv.style.background = '#dcfce7';
                    resultDiv.style.border = '1px solid #86efac';
                    resultDiv.style.color = '#15803d';
                    resultDiv.innerHTML = `<b>Success!</b> Message sent to <b>${{escapeHtml(phone)}}</b> via WhatsApp.`;
                    document.getElementById('directMessageText').value = '';
                    updateDirectPreview();
                    refreshDashboardData(true);
                }} else {{
                    resultDiv.style.background = '#fee2e2';
                    resultDiv.style.border = '1px solid #fca5a5';
                    resultDiv.style.color = '#b91c1c';
                    resultDiv.innerHTML = `<b>Delivery Failed:</b> ${{escapeHtml(res.error || 'Failed to send message')}}`;
                }}
            }} catch (e) {{
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#fee2e2';
                resultDiv.style.border = '1px solid #fca5a5';
                resultDiv.style.color = '#b91c1c';
                resultDiv.innerHTML = `<b>Error:</b> ${{escapeHtml(e.message)}}`;
            }} finally {{
                btn.disabled = false;
                btn.innerHTML = 'Send Direct Message';
            }}
        }}

        window.onclick = function(event) {{
            const modal = document.getElementById('userModal');
            if (event.target == modal) closeUserModal();
        }}
    </script>
</body>
</html>"""
    response = HTMLResponse(content=html)
    q_pass = request.query_params.get("password") or request.query_params.get("pass")
    if q_pass and q_pass == ADMIN_PASSWORD:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=ADMIN_PASSWORD,
            max_age=60 * 60 * 24 * 30,
            httponly=True,
            samesite="lax",
        )
    return response


# Top-level ASGI application fallback if Vercel routes directly to /api/admin
app = FastAPI(title="EdTech Hub Admin Portal")
app.include_router(router, prefix="/admin")
