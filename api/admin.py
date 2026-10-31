"""
api/admin.py - Modern Enterprise Admin & Analytics Dashboard for EdTech Hub.

Features:
- Enterprise SaaS UI with EDTECH company logo branding
- Real-time live data fetching from SQLite/PostgreSQL/Upstash database (ZERO mock/sample data)
- Interactive Chart.js charts (Status Donut, Time-of-Day Donut, 24-Hour Activity Area, 11-Module Funnel)
- Real-time client-side polling / auto-sync (30s) & instant AJAX refresh
- Teacher AI Readiness Survey Breakdown
- Live Learners Table with instant search, filter tabs, direct WhatsApp links
- Student Journey Timeline Modal
- CSV Export for Excel/Sheets
"""

import csv
import io
import json
import os
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
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
        <span>&#x26A0;&#xFE0F;</span> <span>{error}</span>
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


@router.get("/export/csv")
async def export_users_csv(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    users = db.get_all_users()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Phone Number (WhatsApp)", "Phase", "Unit ID", "Lesson Index", "Completed Modules Count",
        "Assessment Answers", "Quiz Answers", "Created At (UTC)", "Last Seen (UTC)", "Total Interactions"
    ])
    for phone, u in users.items():
        writer.writerow([
            phone,
            u.get("phase", "idle"),
            u.get("unit_id", ""),
            u.get("lesson_index", ""),
            len(u.get("completed_lessons") or []),
            json.dumps(u.get("assessment_answers") or {}),
            json.dumps(u.get("quiz_answers") or {}),
            u.get("created_at", ""),
            u.get("last_seen", ""),
            u.get("total_messages", 0),
        ])
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=edtech_learners_report.csv"}
    )


@router.get("", response_class=HTMLResponse)
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
    db_path = data["database_path"].split(os.sep)[-1]

    # Serialize analytics data to JSON string for Chart.js
    analytics_json = json.dumps(data)

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
                        <span>&#x1F4AC;</span> WhatsApp
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
                <button class="btn-action btn-view" onclick="openUserModal('{phone}')">&#x1F441;&#xFE0F; Journey</button>
                <button class="btn-action btn-reset" onclick="resetUser('{phone}')">&#x21BA; Reset</button>
                <button class="btn-action btn-reset" style="color:#ef4444;border-color:#fecaca;" onclick="deleteUser('{phone}')">&#x1F5D1;&#xFE0F; Delete</button>
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
                <div style="font-size:48px;margin-bottom:12px;">&#x1F4F1;</div>
                <h3 style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px;">Waiting for First WhatsApp Learner</h3>
                <p style="font-size:13px;line-height:1.5;margin-bottom:16px;">
                    The system is connected to the live database and monitoring incoming messages. Have a teacher message <b>"hi"</b> on WhatsApp to enroll.
                </p>
                <span class="badge badge-green"><span class="badge-dot"></span> Live DB Sync Ready</span>
            </div>
        </td>
    </tr>
    """

    empty_activity_state = """
    <div style="text-align:center;padding:32px 16px;color:#94a3b8;font-size:13px;">
        <div style="font-size:28px;margin-bottom:8px;">&#x23F3;</div>
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
    <!-- Chart.js 4.4.1 -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
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
                <span>Live DB Connected</span>
            </div>
            <div class="db-badge">
                Backend: {backend.upper()} ({db_path})
            </div>
            <button id="refreshBtn" onclick="refreshDashboardData()" class="btn btn-primary" title="Poll and refresh latest data from live database">
                <span id="refreshIcon">&#x21BB;</span>
                <span>Refresh</span>
            </button>
            <a href="/admin/export/csv" class="btn" title="Download all learner records as CSV">
                <span>&#x1F4E5;</span>
                <span>Export CSV</span>
            </a>
            <a href="/admin/logout" class="btn" title="Sign out from dashboard">
                <span>&#x23FB;</span>
                <span>Logout</span>
            </a>
        </div>
    </header>

    <div class="dashboard-container">
        <!-- Hero KPI Metrics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Total Learners</span>
                    <div class="stat-icon-wrap" style="background:#dbeafe;color:#1d4ed8;">&#x1F465;</div>
                </div>
                <div class="stat-val" id="kpiTotalUsers">{summary['total_users']}</div>
                <div class="stat-meta">Unique phone numbers saved in DB</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Active Learners</span>
                    <div class="stat-icon-wrap" style="background:#eff6ff;color:#2563eb;">&#x1F4D6;</div>
                </div>
                <div class="stat-val" style="color:#2563eb;" id="kpiActiveUsers">{summary['active_learners']}</div>
                <div class="stat-meta">Currently studying modules & quizzes</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Course Completed</span>
                    <div class="stat-icon-wrap" style="background:#dcfce7;color:#15803d;">&#x1F393;</div>
                </div>
                <div class="stat-val" style="color:#10b981;" id="kpiCompletedUsers">{summary['completed_learners']}</div>
                <div class="stat-meta"><b id="kpiCompletionRate">{summary.get('completion_rate', 0)}%</b> graduation completion rate</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">AI Readiness</span>
                    <div class="stat-icon-wrap" style="background:#f3e8ff;color:#7e22ce;">&#x1F9E0;</div>
                </div>
                <div class="stat-val" style="color:#8b5cf6;" id="kpiAssessments">{summary['assessment_completed']}</div>
                <div class="stat-meta">Teachers assessed on AI comfort</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Interactions Logged</span>
                    <div class="stat-icon-wrap" style="background:#fef3c7;color:#b45309;">&#x26A1;</div>
                </div>
                <div class="stat-val" style="color:#d97706;" id="kpiInteractions">{summary['total_interactions']}</div>
                <div class="stat-meta">Messages, quizzes & AI questions</div>
            </div>

            <div class="stat-card">
                <div class="stat-top">
                    <span class="stat-label">Peak Learning Time</span>
                    <div class="stat-icon-wrap" style="background:#fee2e2;color:#b91c1c;">&#x23F0;</div>
                </div>
                <div class="stat-val" style="font-size:24px;padding-top:4px;" id="kpiPeakHour">{summary['peak_hour_utc']}</div>
                <div class="stat-meta">Most active study hour across teachers</div>
            </div>
        </div>

        <!-- Charts Row 1: Pie / Donut Charts -->
        <div class="charts-row-2col">
            <!-- Pie Chart 1: Learner Status Breakdown -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-wrap">
                        <span style="font-size:20px;">&#x1F3AF;</span>
                        <div>
                            <h2 class="chart-card-title">Learner Status Distribution</h2>
                            <p class="chart-subtitle">Real-time breakdown of where students currently are in the course</p>
                        </div>
                    </div>
                </div>
                <div class="canvas-container">
                    <canvas id="statusDonutChart"></canvas>
                </div>
            </div>

            <!-- Pie Chart 2: Time-of-Day Study Habits -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-wrap">
                        <span style="font-size:20px;">&#x1F305;</span>
                        <div>
                            <h2 class="chart-card-title">When Are They Learning? (Time of Day)</h2>
                            <p class="chart-subtitle">Teacher learning activity categorized by morning, afternoon, evening, and night</p>
                        </div>
                    </div>
                </div>
                <div class="canvas-container">
                    <canvas id="timeOfDayChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Charts Row 2: 24-Hour Activity Rhythm & 11-Module Progression Funnel -->
        <div class="charts-row-3col">
            <!-- 24-Hour Activity Line/Area Curve -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-wrap">
                        <span style="font-size:20px;">&#x1F4C8;</span>
                        <div>
                            <h2 class="chart-card-title">24-Hour Learning Rhythm (UTC)</h2>
                            <p class="chart-subtitle">Hourly distribution of all user messages, quizzes, and AI tutor queries</p>
                        </div>
                    </div>
                </div>
                <div class="canvas-container" style="min-height: 260px;">
                    <canvas id="hourlyActivityChart"></canvas>
                </div>
            </div>

            <!-- 11-Module Progression Funnel -->
            <div class="chart-card">
                <div class="chart-card-header">
                    <div class="chart-title-wrap">
                        <span style="font-size:20px;">&#x1F522;</span>
                        <div>
                            <h2 class="chart-card-title">11-Module Funnel</h2>
                            <p class="chart-subtitle">Learner progression & drop-off</p>
                        </div>
                    </div>
                </div>
                <div class="canvas-container" style="min-height: 260px;">
                    <canvas id="funnelBarChart"></canvas>
                </div>
            </div>
        </div>

        <!-- AI Readiness Survey Section -->
        <div class="chart-card" style="margin-bottom: 28px;">
            <div class="chart-card-header">
                <div class="chart-title-wrap">
                    <span style="font-size:20px;">&#x1F4CA;</span>
                    <div>
                        <h2 class="chart-card-title">Teacher AI Readiness Survey Insights</h2>
                        <p class="chart-subtitle">Aggregated self-assessment data collected directly from educators</p>
                    </div>
                </div>
            </div>
            <div class="insights-grid" id="surveyInsightsGrid">
                <!-- Injected via JavaScript from real DB data -->
            </div>
        </div>

        <!-- Learners Table & Live Activity Feed -->
        <div class="section-split">
            <!-- Learners Data Table -->
            <div class="table-card">
                <div class="table-toolbar">
                    <div>
                        <h2 style="font-size:16px;font-weight:700;color:#0f172a;display:flex;align-items:center;gap:8px;">
                            <span>&#x1F465;</span>
                            <span>Learner Registry (<span id="tableCount">{len(users_list)}</span>)</span>
                        </h2>
                        <p style="font-size:12px;color:var(--text-muted);margin-top:2px;">All educators registered through WhatsApp</p>
                    </div>
                    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
                        <input type="text" id="userSearch" class="search-input" placeholder="Search phone number..." oninput="filterTable()">
                        <div class="filter-pills">
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
                        <span style="font-size:18px;">&#x26A1;</span>
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
        // Global Chart Instances
        let statusChart = null;
        let todChart = null;
        let hourlyChart = null;
        let funnelChart = null;
        let currentFilter = 'all';

        // Load initial data from server
        let dashboardData = JSON.parse(document.getElementById('initialData').textContent);

        document.addEventListener('DOMContentLoaded', () => {{
            renderAllCharts(dashboardData);
            renderSurveyCards(dashboardData.assessment_insights);

            // Auto-sync polling every 30 seconds
            setInterval(() => {{
                refreshDashboardData(true);
            }}, 30000);
        }});

        function renderAllCharts(data) {{
            // 1. Donut Chart: Learner Status Distribution
            const statusCtx = document.getElementById('statusDonutChart').getContext('2d');
            const statusData = data.status_distribution || {{ labels: [], counts: [] }};
            const hasStatusData = statusData.counts && statusData.counts.some(c => c > 0);

            if (statusChart) statusChart.destroy();
            statusChart = new Chart(statusCtx, {{
                type: 'doughnut',
                data: {{
                    labels: statusData.labels,
                    datasets: [{{
                        data: hasStatusData ? statusData.counts : [1],
                        backgroundColor: hasStatusData
                            ? ['#10b981', '#2563eb', '#f59e0b', '#8b5cf6', '#ec4899', '#94a3b8']
                            : ['#e2e8f0'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                        hoverOffset: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                boxWidth: 12,
                                padding: 14,
                                font: {{ family: 'Inter', size: 11, weight: '600' }}
                            }}
                        }},
                        tooltip: {{
                            enabled: hasStatusData,
                            callbacks: {{
                                label: (ctx) => ` ${{ctx.label}}: ${{ctx.raw}} learners`
                            }}
                        }}
                    }}
                }}
            }});

            // 2. Donut Chart: Time of Day Habits
            const todCtx = document.getElementById('timeOfDayChart').getContext('2d');
            const todData = data.when_are_they_learning || {{}};
            const todCounts = todData.time_of_day_counts || [0, 0, 0, 0];
            const hasTodData = todCounts.some(c => c > 0);

            if (todChart) todChart.destroy();
            todChart = new Chart(todCtx, {{
                type: 'doughnut',
                data: {{
                    labels: todData.time_of_day_labels || ['Morning', 'Afternoon', 'Evening', 'Night'],
                    datasets: [{{
                        data: hasTodData ? todCounts : [1],
                        backgroundColor: hasTodData
                            ? ['#38bdf8', '#f59e0b', '#6366f1', '#1e293b']
                            : ['#e2e8f0'],
                        borderWidth: 2,
                        borderColor: '#ffffff',
                        hoverOffset: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                boxWidth: 12,
                                padding: 14,
                                font: {{ family: 'Inter', size: 11, weight: '600' }}
                            }}
                        }},
                        tooltip: {{
                            enabled: hasTodData,
                            callbacks: {{
                                label: (ctx) => ` ${{ctx.label}}: ${{ctx.raw}} study events`
                            }}
                        }}
                    }}
                }}
            }});

            // 3. Smooth Area Chart: 24-Hour Activity (UTC)
            const hourlyCtx = document.getElementById('hourlyActivityChart').getContext('2d');
            const hourlyCounts = todData.hourly_counts || new Array(24).fill(0);
            const hourlyLabels = todData.hourly_labels || Array.from({{length: 24}}, (_, i) => `${{i.toString().padStart(2, '0')}}:00`);

            const gradient = hourlyCtx.createLinearGradient(0, 0, 0, 240);
            gradient.addColorStop(0, 'rgba(37, 99, 235, 0.35)');
            gradient.addColorStop(1, 'rgba(37, 99, 235, 0.01)');

            if (hourlyChart) hourlyChart.destroy();
            hourlyChart = new Chart(hourlyCtx, {{
                type: 'line',
                data: {{
                    labels: hourlyLabels,
                    datasets: [{{
                        label: 'Study & Message Events',
                        data: hourlyCounts,
                        borderColor: '#2563eb',
                        borderWidth: 2.5,
                        backgroundColor: gradient,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 3,
                        pointBackgroundColor: '#2563eb',
                        pointHoverRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{ precision: 0, font: {{ family: 'Inter', size: 11 }} }},
                            grid: {{ color: '#f1f5f9' }}
                        }},
                        x: {{
                            ticks: {{ font: {{ family: 'Inter', size: 10 }}, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 }},
                            grid: {{ display: false }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                title: (ctx) => `${{ctx[0].label}} UTC`,
                                label: (ctx) => ` ${{ctx.raw}} interactions`
                            }}
                        }}
                    }}
                }}
            }});

            // 4. Bar Chart: 11-Module Progression Funnel
            const funnelCtx = document.getElementById('funnelBarChart').getContext('2d');
            const funnelCounts = data.progression_funnel ? data.progression_funnel.lesson_counts : new Array(11).fill(0);
            const funnelLabels = data.progression_funnel ? data.progression_funnel.labels : Array.from({{length: 11}}, (_, i) => `Mod ${{i+1}}`);

            if (funnelChart) funnelChart.destroy();
            funnelChart = new Chart(funnelCtx, {{
                type: 'bar',
                data: {{
                    labels: funnelLabels,
                    datasets: [{{
                        label: 'Learners at Step',
                        data: funnelCounts,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6,
                        hoverBackgroundColor: '#1d4ed8'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{ precision: 0, font: {{ family: 'Inter', size: 11 }} }},
                            grid: {{ color: '#f1f5f9' }}
                        }},
                        x: {{
                            ticks: {{ font: {{ family: 'Inter', size: 10 }} }},
                            grid: {{ display: false }}
                        }}
                    }},
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{
                            callbacks: {{
                                label: (ctx) => ` ${{ctx.raw}} active students`
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function renderSurveyCards(insights) {{
            const grid = document.getElementById('surveyInsightsGrid');
            if (!insights) return;

            grid.innerHTML = `
                <div class="insight-card">
                    <h4><span>&#x1F4CA;</span> AI Usage Frequency</h4>
                    <div class="insight-row"><span>Never tried yet:</span><b>${{insights.ai_use['Never'] || 0}}</b></div>
                    <div class="insight-row"><span>Sometimes:</span><b>${{insights.ai_use['Sometimes'] || 0}}</b></div>
                    <div class="insight-row"><span>Regularly:</span><b>${{insights.ai_use['Regularly'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4><span>&#x1F9E0;</span> Confidence Level</h4>
                    <div class="insight-row"><span>Not confident:</span><b>${{insights.comfort['Not confident'] || 0}}</b></div>
                    <div class="insight-row"><span>Somewhat confident:</span><b>${{insights.comfort['Somewhat confident'] || 0}}</b></div>
                    <div class="insight-row"><span>Very confident:</span><b>${{insights.comfort['Very confident'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4><span>&#x26A0;&#xFE0F;</span> Primary Challenge</h4>
                    <div class="insight-row"><span>Where to start:</span><b>${{insights.challenge["Don't know where to start"] || 0}}</b></div>
                    <div class="insight-row"><span>Limited access/devices:</span><b>${{insights.challenge['Limited access/internet'] || 0}}</b></div>
                    <div class="insight-row"><span>Misuse worries:</span><b>${{insights.challenge['Worried about misuse'] || 0}}</b></div>
                </div>
                <div class="insight-card">
                    <h4><span>&#x1F3AF;</span> Primary Course Goal</h4>
                    <div class="insight-row"><span>Practical lesson ideas:</span><b>${{insights.goal['Practical lesson ideas'] || 0}}</b></div>
                    <div class="insight-row"><span>Time-saving tools:</span><b>${{insights.goal['Time-saving tools'] || 0}}</b></div>
                    <div class="insight-row"><span>Safe/Responsible AI:</span><b>${{insights.goal['Responsible & safe AI'] || 0}}</b></div>
                </div>
            `;
        }}

        async function refreshDashboardData(silent = false) {{
            const btn = document.getElementById('refreshBtn');
            const icon = document.getElementById('refreshIcon');
            if (!silent && icon) icon.classList.add('spinning');

            try {{
                const resp = await fetch('/admin/api/analytics');
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

                // Update Charts
                renderAllCharts(data);
                renderSurveyCards(data.assessment_insights);

                // Re-render Table
                renderTableRows(data.users);

                // Re-render Activity Stream
                renderActivityFeed(data.recent_activity);

            }} catch (err) {{
                console.error('Refresh error:', err);
            }} finally {{
                if (icon) icon.classList.remove('spinning');
            }}
        }}

        function renderTableRows(users) {{
            const tbody = document.getElementById('learnersTableBody');
            if (!users || users.length === 0) {{
                tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;padding:48px 24px;">
                        <div style="max-width:440px;margin:0 auto;color:#64748b;">
                            <div style="font-size:48px;margin-bottom:12px;">&#x1F4F1;</div>
                            <h3 style="font-size:16px;font-weight:700;color:#0f172a;margin-bottom:6px;">Waiting for First WhatsApp Learner</h3>
                            <p style="font-size:13px;line-height:1.5;">The system is live and recording. Have a student message the bot on WhatsApp to see live metrics.</p>
                        </div>
                    </td>
                </tr>`;
                return;
            }}

            let html = '';
            users.forEach(u => {{
                const phone = u.phone_number;
                const phase = u.phase;
                const pct = u.progress_percent;
                const mod_title = u.current_module_title;
                const last_seen = u.last_seen_relative;
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
                <tr data-phone="${{phone}}" data-category="${{row_category}}">
                    <td class="cell-phone">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-weight:700;color:#0f172a;">${{phone}}</span>
                            <a href="https://wa.me/${{clean_phone}}" target="_blank" rel="noopener noreferrer" class="wa-btn" title="Open chat with teacher on WhatsApp">
                                <span>&#x1F4AC;</span> WhatsApp
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
                        <button class="btn-action btn-view" onclick="openUserModal('${{phone}}')">&#x1F441;&#xFE0F; Journey</button>
                        <button class="btn-action btn-reset" onclick="resetUser('${{phone}}')">&#x21BA; Reset</button>
                        <button class="btn-action btn-reset" style="color:#ef4444;border-color:#fecaca;" onclick="deleteUser('${{phone}}')">&#x1F5D1;&#xFE0F; Delete</button>
                    </td>
                </tr>`;
            }});
            tbody.innerHTML = html;
            filterTable();
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
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
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
                const resp = await fetch('/admin/api/user/' + encodeURIComponent(phone));
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
                        <div><b>Current Step:</b> ${{u.lesson_index !== null ? 'Module ' + (u.lesson_index + 1) : 'None'}}</div>
                        <div><b>Total Interactions:</b> ${{u.total_messages || 0}} msgs</div>
                        <div><b>Completed Modules:</b> ${{(u.completed_lessons || []).length}} / 11</div>
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
                const resp = await fetch('/admin/api/user/' + encodeURIComponent(phone) + '/reset', {{ method: 'POST' }});
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
                const resp = await fetch('/admin/api/user/' + encodeURIComponent(phone) + '/delete', {{ method: 'POST' }});
                if (resp.ok) {{
                    refreshDashboardData();
                }} else {{
                    alert('Failed to delete student.');
                }}
            }} catch (e) {{
                alert('Error: ' + e.message);
            }}
        }}

        window.onclick = function(event) {{
            const modal = document.getElementById('userModal');
            if (event.target == modal) closeUserModal();
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# Top-level fallback for admin mounted app
app = router
