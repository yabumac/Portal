"""
api/admin.py - Modern Admin & Analytics Dashboard for WhatsApp Learning Bot.

Features:
- Authentication via ADMIN_PASSWORD (cookie session or URL param)
- Overview KPI metrics (Total Users, Active, Completed, Assessment, Total Interactions)
- "When are they learning?" Hourly (0-23) & Day of Week analytics
- Course Progression Funnel (Modules 1 - 11)
- Assessment Insights (AI usage, confidence, challenges, goals)
- Learners Table with search, status filters, progress bars, direct WhatsApp link
- User Learning Journey modal / timeline
- CSV export for reporting
"""

import csv
import io
import json
import os
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

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


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: Optional[str] = None):
    error_banner = f"""
    <div style="background:#fee2e2;border:1px solid #ef4444;color:#b91c1c;padding:12px 16px;border-radius:8px;margin-bottom:16px;font-size:14px;">
        {error}
    </div>
    """ if error else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - EdTech Hub</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f1f5f9;
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
            max-width: 400px;
            width: 100%;
            padding: 32px;
            border: 1px solid #e2e8f0;
        }}
        .logo {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
        }}
        .logo-icon {{
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-weight: 700;
            font-size: 20px;
        }}
        .logo-text h1 {{ font-size: 20px; font-weight: 700; color: #0f172a; }}
        .logo-text p {{ font-size: 13px; color: #64748b; }}
        label {{ display: block; font-size: 14px; font-weight: 600; color: #334155; margin-bottom: 6px; }}
        input[type="password"] {{
            width: 100%;
            padding: 12px 14px;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            font-size: 15px;
            outline: none;
            transition: border-color 0.2s;
        }}
        input[type="password"]:focus {{
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }}
        button {{
            width: 100%;
            padding: 12px;
            background: #2563eb;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            margin-top: 18px;
            transition: background 0.2s;
        }}
        button:hover {{ background: #1d4ed8; }}
        .hint {{ font-size: 12px; color: #94a3b8; text-align: center; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <div class="logo-icon">&#x1F4DA;</div>
            <div class="logo-text">
                <h1>EdTech Hub Portal</h1>
                <p>Admin Analytics Dashboard</p>
            </div>
        </div>
        {error_banner}
        <form method="post" action="/admin/login">
            <div>
                <label for="password">Admin Password</label>
                <input type="password" id="password" name="password" required autofocus placeholder="Enter admin password">
            </div>
            <button type="submit">Sign In to Dashboard</button>
        </form>
        <p class="hint">Default password is <code>admin123</code> (configurable via ADMIN_PASSWORD)</p>
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
    return RedirectResponse(url="/admin/login?error=Invalid%20password", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@router.get("/api/analytics")
async def get_analytics_json(request: Request):
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


@router.get("/export/csv")
async def export_users_csv(request: Request):
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    users = db.get_all_users()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Phone Number", "Phase", "Unit", "Lesson Index", "Completed Lessons Count",
        "Assessment Answers", "Created At", "Last Seen", "Total Interactions"
    ])
    for phone, u in users.items():
        writer.writerow([
            phone,
            u.get("phase", "idle"),
            u.get("unit_id", ""),
            u.get("lesson_index", ""),
            len(u.get("completed_lessons") or []),
            json.dumps(u.get("assessment_answers") or {}),
            u.get("created_at", ""),
            u.get("last_seen", ""),
            u.get("total_messages", 0),
        ])
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=edtech_users.csv"}
    )


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login")

    data = db.get_analytics_summary()
    summary = data["summary"]
    when = data["when_are_they_learning"]
    hourly = when["hourly_counts"]
    max_hour_val = max(hourly) if hourly and max(hourly) > 0 else 1

    # Format hourly chart bars HTML
    hourly_bars_html = ""
    for hour in range(24):
        count = hourly[hour]
        pct = int((count / max_hour_val) * 100) if max_hour_val > 0 else 0
        h_label = f"{hour:02d}:00"
        bar_bg = "#2563eb" if count > 0 else "#e2e8f0"
        hourly_bars_html += f"""
        <div class="chart-col" title="{h_label} UTC: {count} actions">
            <div class="chart-val">{count if count > 0 else ''}</div>
            <div class="chart-bar-wrap">
                <div class="chart-bar" style="height:{max(pct, 4 if count > 0 else 2)}%;background:{bar_bg};"></div>
            </div>
            <div class="chart-label">{hour}h</div>
        </div>
        """

    # Time of Day breakdown HTML
    tod = when["time_of_day"]
    tod_html = ""
    tod_icons = {"Morning": "&#x1F305;", "Afternoon": "&#x2600;&#xFE0F;", "Evening": "&#x1F307;", "Night": "&#x1F319;"}
    for period, cnt in tod.items():
        key = period.split()[0]
        icon = tod_icons.get(key, "&#x23F0;")
        tod_html += f"""
        <div class="tod-card">
            <div class="tod-header">
                <span class="tod-icon">{icon}</span>
                <span class="tod-name">{period}</span>
            </div>
            <div class="tod-num">{cnt} <span class="tod-sub">events</span></div>
        </div>
        """

    # Days of week HTML
    daily = when["daily_counts"]
    max_day_val = max([d["count"] for d in daily]) if daily and max([d["count"] for d in daily]) > 0 else 1
    daily_bars_html = ""
    for d in daily:
        c = d["count"]
        pct = int((c / max_day_val) * 100) if max_day_val > 0 else 0
        daily_bars_html += f"""
        <div class="chart-col" title="{d['day']}: {c} actions">
            <div class="chart-val">{c if c > 0 else ''}</div>
            <div class="chart-bar-wrap">
                <div class="chart-bar" style="height:{max(pct, 4 if c > 0 else 2)}%;background:#0ea5e9;"></div>
            </div>
            <div class="chart-label">{d['day']}</div>
        </div>
        """

    # Progression funnel (11 modules)
    funnel_counts = data["progression_funnel"]["lesson_counts"]
    funnel_html = ""
    for i in range(11):
        cnt = funnel_counts[i]
        mod_num = i + 1
        pct = int((cnt / max(summary["total_users"], 1)) * 100)
        funnel_html += f"""
        <div class="funnel-step">
            <div class="funnel-header">
                <span class="funnel-title">Module {mod_num}</span>
                <span class="funnel-count">{cnt} learners ({pct}%)</span>
            </div>
            <div class="funnel-bar-bg">
                <div class="funnel-bar-fill" style="width:{pct}%;"></div>
            </div>
        </div>
        """

    # Assessment insights cards
    ai_insights = data["assessment_insights"]
    assessment_html = f"""
    <div class="insights-grid">
        <div class="insight-card">
            <h4>AI Usage Frequency</h4>
            <div class="insight-row"><span>Never tried:</span><b>{ai_insights['ai_use']['Never']}</b></div>
            <div class="insight-row"><span>Sometimes:</span><b>{ai_insights['ai_use']['Sometimes']}</b></div>
            <div class="insight-row"><span>Regularly:</span><b>{ai_insights['ai_use']['Regularly']}</b></div>
        </div>
        <div class="insight-card">
            <h4>Confidence Level</h4>
            <div class="insight-row"><span>Not confident:</span><b>{ai_insights['comfort']['Not confident']}</b></div>
            <div class="insight-row"><span>Somewhat:</span><b>{ai_insights['comfort']['Somewhat confident']}</b></div>
            <div class="insight-row"><span>Very confident:</span><b>{ai_insights['comfort']['Very confident']}</b></div>
        </div>
        <div class="insight-card">
            <h4>Primary Challenge</h4>
            <div class="insight-row"><span>Where to start:</span><b>{ai_insights['challenge']['Don\'t know where to start']}</b></div>
            <div class="insight-row"><span>Devices/Internet:</span><b>{ai_insights['challenge']['Limited access/internet']}</b></div>
            <div class="insight-row"><span>Misuse worries:</span><b>{ai_insights['challenge']['Worried about misuse']}</b></div>
        </div>
        <div class="insight-card">
            <h4>Primary Goal</h4>
            <div class="insight-row"><span>Practical ideas:</span><b>{ai_insights['goal']['Practical lesson ideas']}</b></div>
            <div class="insight-row"><span>Time saving:</span><b>{ai_insights['goal']['Time-saving tools']}</b></div>
            <div class="insight-row"><span>Safe/Responsible:</span><b>{ai_insights['goal']['Responsible & safe AI']}</b></div>
        </div>
    </div>
    """

    # User table rows
    users_list = data["users"]
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

        # Badge color
        if phase == "complete":
            badge_class = "badge-green"
            badge_text = "Completed"
        elif phase in ("lesson", "quiz"):
            badge_class = "badge-blue"
            badge_text = f"In Progress ({phase.capitalize()})"
        elif phase == "tutor":
            badge_class = "badge-purple"
            badge_text = "AI Tutor"
        elif phase == "assessment":
            badge_class = "badge-orange"
            badge_text = "Self-Assessment"
        else:
            badge_class = "badge-gray"
            badge_text = "Idle"

        assess_badge = "badge-green" if assess_done == "Completed" else "badge-gray"

        users_rows_html += f"""
        <tr data-phone="{phone}" data-phase="{phase}">
            <td class="cell-phone">
                <a href="https://wa.me/{phone.replace('+', '')}" target="_blank" title="Open in WhatsApp" class="phone-link">
                    &#x1F4AC; {phone}
                </a>
            </td>
            <td><span class="badge {badge_class}">{badge_text}</span></td>
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
            <td style="text-align:center;">{messages}</td>
            <td><span class="badge {assess_badge}">{assess_done}</span></td>
            <td class="cell-actions">
                <button class="btn-action btn-view" onclick="openUserModal('{phone}')">Journey</button>
                <button class="btn-action btn-reset" onclick="resetUser('{phone}')">Reset</button>
            </td>
        </tr>
        """

    # Recent activity logs feed
    recent_activity = data["recent_activity"]
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
                <div class="act-desc"><b>{ev}</b> - {det}</div>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EdTech Hub - Admin Dashboard</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --surface: #ffffff;
            --bg: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --radius: 12px;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 24px 32px;
            min-height: 100vh;
        }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .brand {{ display: flex; align-items: center; gap: 14px; }}
        .brand-icon {{
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #2563eb, #1e40af);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 22px;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
        }}
        .brand h1 {{ font-size: 22px; font-weight: 700; }}
        .brand p {{ font-size: 13px; color: var(--text-muted); }}
        .header-actions {{ display: flex; align-items: center; gap: 12px; }}
        .db-status-pill {{
            background: #dcfce7;
            border: 1px solid #86efac;
            color: #166534;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .db-dot {{ width: 8px; height: 8px; background: #22c55e; border-radius: 50%; }}
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
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn:hover {{ background: #f1f5f9; }}
        .btn-primary {{ background: var(--primary); color: #fff; border-color: var(--primary); }}
        .btn-primary:hover {{ background: var(--primary-dark); }}

        /* Top KPI Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }}
        .stat-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            position: relative;
        }}
        .stat-label {{ font-size: 13px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }}
        .stat-value {{ font-size: 30px; font-weight: 800; color: var(--text-main); }}
        .stat-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}

        /* Sections */
        .section-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            margin-bottom: 28px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }}
        .section-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .section-title {{ font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}

        /* "When are they learning?" Hourly Chart */
        .analytics-two-col {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }}
        @media(max-width: 900px) {{
            .analytics-two-col {{ grid-template-columns: 1fr; }}
            body {{ padding: 16px; }}
        }}
        .chart-container {{
            display: flex;
            align-items: flex-end;
            gap: 6px;
            height: 160px;
            padding-top: 24px;
            border-bottom: 1px solid var(--border);
            overflow-x: auto;
        }}
        .chart-col {{
            flex: 1;
            min-width: 22px;
            display: flex;
            flex-direction: column;
            align-items: center;
            height: 100%;
            justify-content: flex-end;
        }}
        .chart-val {{ font-size: 10px; font-weight: 700; color: var(--text-muted); margin-bottom: 4px; min-height: 12px; }}
        .chart-bar-wrap {{ width: 100%; height: 110px; display: flex; align-items: flex-end; }}
        .chart-bar {{ width: 100%; border-radius: 4px 4px 0 0; transition: height 0.3s ease; }}
        .chart-label {{ font-size: 10px; color: var(--text-muted); margin-top: 6px; }}

        .tod-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
        .tod-card {{
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
        }}
        .tod-header {{ display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--text-muted); }}
        .tod-num {{ font-size: 20px; font-weight: 800; color: var(--text-main); margin-top: 6px; }}
        .tod-sub {{ font-size: 11px; font-weight: normal; color: var(--text-muted); }}

        /* Funnel */
        .funnel-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }}
        .funnel-step {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px; }}
        .funnel-header {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 600; margin-bottom: 6px; }}
        .funnel-count {{ color: var(--primary); font-weight: 700; }}
        .funnel-bar-bg {{ background: #e2e8f0; height: 8px; border-radius: 4px; overflow: hidden; }}
        .funnel-bar-fill {{ background: var(--primary); height: 100%; border-radius: 4px; }}

        /* Assessment cards */
        .insights-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
        .insight-card {{ background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
        .insight-card h4 {{ font-size: 13px; font-weight: 700; margin-bottom: 12px; color: #334155; }}
        .insight-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed #e2e8f0; }}

        /* Table */
        .table-filter-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 16px;
            flex-wrap: wrap;
        }}
        .search-box {{
            padding: 8px 14px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            width: 280px;
            outline: none;
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
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }}
        tr:hover td {{ background: #f8fafc; }}
        .cell-phone {{ font-weight: 600; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }}
        .phone-link {{ color: var(--primary); text-decoration: none; }}
        .phone-link:hover {{ text-decoration: underline; }}
        .progress-wrap {{ display: flex; align-items: center; gap: 8px; }}
        .progress-bar-bg {{ background: #e2e8f0; border-radius: 4px; height: 6px; width: 80px; overflow: hidden; }}
        .progress-bar-fill {{ background: #10b981; height: 100%; }}
        .progress-pct {{ font-size: 11px; font-weight: 700; }}
        .module-title-sub {{ font-size: 11px; color: var(--text-muted); margin-top: 3px; }}

        /* Badges */
        .badge {{
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            display: inline-block;
        }}
        .badge-green {{ background: #dcfce7; color: #15803d; }}
        .badge-blue {{ background: #dbeafe; color: #1e40af; }}
        .badge-purple {{ background: #f3e8ff; color: #7e22ce; }}
        .badge-orange {{ background: #ffedd5; color: #c2410c; }}
        .badge-gray {{ background: #f1f5f9; color: #475569; }}

        .cell-actions {{ display: flex; gap: 6px; }}
        .btn-action {{
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border);
            cursor: pointer;
            background: #fff;
        }}
        .btn-view {{ color: var(--primary); border-color: #bfdbfe; }}
        .btn-view:hover {{ background: #eff6ff; }}
        .btn-reset {{ color: #dc2626; border-color: #fecaca; }}
        .btn-reset:hover {{ background: #fef2f2; }}

        /* Activity Feed */
        .activity-feed {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            max-height: 340px;
            overflow-y: auto;
        }}
        .activity-item {{
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 8px 12px;
            background: #f8fafc;
            border-radius: 8px;
            font-size: 12px;
        }}
        .act-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--primary); margin-top: 5px; flex-shrink: 0; }}
        .act-body {{ flex: 1; }}
        .act-header {{ display: flex; justify-content: space-between; margin-bottom: 2px; }}
        .act-phone {{ font-weight: 600; color: #1e293b; font-family: monospace; }}
        .act-time {{ color: var(--text-muted); font-size: 11px; }}
        .act-desc {{ color: #475569; }}

        /* Modal */
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(15, 23, 42, 0.6);
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }}
        .modal-content {{
            background: #fff;
            border-radius: 16px;
            max-width: 650px;
            width: 100%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
        }}
        .modal-header {{
            padding: 20px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-body {{
            padding: 20px;
            overflow-y: auto;
            flex: 1;
        }}
        .close-btn {{
            background: none;
            border: none;
            font-size: 20px;
            cursor: pointer;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <div class="brand-icon">&#x1F4DA;</div>
            <div>
                <h1>EdTech Hub Learning Portal</h1>
                <p>Real-Time Course Analytics & Learner Management</p>
            </div>
        </div>
        <div class="header-actions">
            <div class="db-status-pill">
                <span class="db-dot"></span>
                <span>Active DB: <b>{data['backend'].upper()}</b> ({data['database_path'].split(os.sep)[-1]})</span>
            </div>
            <a href="/admin/export/csv" class="btn">&#x1F4E5; Export CSV</a>
            <button onclick="location.reload()" class="btn">&#x21BB; Refresh</button>
            <a href="/admin/logout" class="btn">&#x23FB; Logout</a>
        </div>
    </header>

    <!-- Top KPI Metrics -->
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-label">Total Learners</div>
            <div class="stat-value">{summary['total_users']}</div>
            <div class="stat-sub">Registered via WhatsApp phone #</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Active Learners</div>
            <div class="stat-value" style="color:#2563eb;">{summary['active_learners']}</div>
            <div class="stat-sub">Currently progressing through lessons</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Course Completed</div>
            <div class="stat-value" style="color:#10b981;">{summary['completed_learners']}</div>
            <div class="stat-sub">Graduated all 11 modules</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">AI Assessments</div>
            <div class="stat-value" style="color:#8b5cf6;">{summary['assessment_completed']}</div>
            <div class="stat-sub">Educators assessed readiness</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Interactions Logged</div>
            <div class="stat-value">{summary['total_interactions']}</div>
            <div class="stat-sub">Peak hour: {summary['peak_hour_utc']}</div>
        </div>
    </div>

    <!-- "When Are They Learning?" Analytics Section -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-title">&#x1F4C8; When Are They Learning? (Activity Time Distribution)</div>
            <span style="font-size:12px;color:var(--text-muted);">Timestamp: UTC (Peak: {summary['peak_hour_utc']})</span>
        </div>
        <div class="analytics-two-col">
            <div>
                <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px;">
                    Hourly distribution of all learner pings, quiz answers, and tutor questions across 24 hours:
                </p>
                <div class="chart-container">
                    {hourly_bars_html}
                </div>
            </div>
            <div>
                <p style="font-size:13px;color:var(--text-muted);margin-bottom:12px;">Time of Day Breakdown:</p>
                <div class="tod-grid">
                    {tod_html}
                </div>
                <div style="margin-top:16px;">
                    <p style="font-size:12px;color:var(--text-muted);margin-bottom:6px;">Daily Activity Breakdown:</p>
                    <div style="display:flex;height:60px;align-items:flex-end;gap:8px;">
                        {daily_bars_html}
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Course Progression Funnel (11 Modules) -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-title">&#x1F393; 11-Module Progression Funnel</div>
            <span style="font-size:12px;color:var(--text-muted);">Learner distribution across modules</span>
        </div>
        <div class="funnel-grid">
            {funnel_html}
        </div>
    </div>

    <!-- AI Readiness Assessment Insights -->
    <div class="section-card">
        <div class="section-header">
            <div class="section-title">&#x1F9E0; Educator AI Readiness Survey Results</div>
            <span style="font-size:12px;color:var(--text-muted);">{summary['assessment_completed']} completed questionnaires</span>
        </div>
        {assessment_html}
    </div>

    <!-- Learners Table & Live Activity Stream -->
    <div style="display:grid;grid-template-columns:2fr 1fr;gap:24px;">
        <!-- Learners Table -->
        <div class="section-card" style="margin-bottom:0;">
            <div class="section-header">
                <div class="section-title">&#x1F465; All Registered Learners ({len(users_list)})</div>
                <input type="text" id="userSearch" class="search-box" placeholder="Search phone number..." oninput="filterTable()">
            </div>
            <div style="overflow-x:auto;">
                <table id="learnersTable">
                    <thead>
                        <tr>
                            <th>Phone (WhatsApp)</th>
                            <th>Status</th>
                            <th>Progress</th>
                            <th>Last Active</th>
                            <th>Msgs</th>
                            <th>Assessment</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users_rows_html if users_rows_html else '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:32px;">No learners have messaged the bot yet. Send "hi" in WhatsApp to register!</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Live Activity Stream -->
        <div class="section-card" style="margin-bottom:0;">
            <div class="section-header">
                <div class="section-title">&#x26A1; Recent Learning Events</div>
            </div>
            <div class="activity-feed">
                {activity_items_html if activity_items_html else '<p style="color:#94a3b8;font-size:13px;padding:20px;text-align:center;">No recent events logged yet.</p>'}
            </div>
        </div>
    </div>

    <!-- User Journey Modal -->
    <div id="userModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">Learner Journey</h3>
                <button class="close-btn" onclick="closeUserModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody">
                <p>Loading journey details...</p>
            </div>
        </div>
    </div>

    <script>
        function filterTable() {{
            const query = document.getElementById("userSearch").value.toLowerCase();
            const rows = document.querySelectorAll("#learnersTable tbody tr");
            rows.forEach(row => {{
                const phone = (row.getAttribute("data-phone") || "").toLowerCase();
                row.style.display = phone.includes(query) ? "" : "none";
            }});
        }}

        async function openUserModal(phone) {{
            const modal = document.getElementById("userModal");
            const modalTitle = document.getElementById("modalTitle");
            const modalBody = document.getElementById("modalBody");
            modalTitle.innerText = "Learner Journey: " + phone;
            modal.style.display = "flex";
            modalBody.innerHTML = "<p>Loading history from database...</p>";

            try {{
                const resp = await fetch("/admin/api/user/" + encodeURIComponent(phone));
                if (!resp.ok) throw new Error("Failed to load user");
                const data = await resp.json();
                const u = data.user;
                const hist = data.history;

                let histHtml = "";
                if (hist && hist.length > 0) {{
                    hist.forEach(item => {{
                        histHtml += `
                        <div style="padding:10px;border-left:3px solid #2563eb;background:#f8fafc;margin-bottom:8px;border-radius:0 8px 8px 0;">
                            <div style="display:flex;justify-content:space-between;font-size:11px;color:#64748b;">
                                <b>${{item.event_type.replace('_', ' ').toUpperCase()}}</b>
                                <span>${{new Date(item.timestamp).toLocaleString()}}</span>
                            </div>
                            <div style="font-size:13px;margin-top:4px;color:#1e293b;">${{item.details || 'Message received'}}</div>
                        </div>`;
                    }});
                }} else {{
                    histHtml = "<p style='color:#94a3b8;'>No timeline entries recorded yet.</p>";
                }}

                modalBody.innerHTML = `
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;background:#f1f5f9;padding:12px;border-radius:8px;font-size:12px;">
                        <div><b>Phone:</b> ${{u.phone_number}}</div>
                        <div><b>Current Phase:</b> ${{u.phase}}</div>
                        <div><b>Current Module:</b> ${{u.lesson_index !== null ? 'Module ' + (u.lesson_index + 1) : 'None'}}</div>
                        <div><b>Total Messages:</b> ${{u.total_messages || 0}}</div>
                        <div><b>First Seen:</b> ${{u.created_at ? new Date(u.created_at).toLocaleDateString() : 'Unknown'}}</div>
                        <div><b>Last Active:</b> ${{u.last_seen ? new Date(u.last_seen).toLocaleString() : 'Unknown'}}</div>
                    </div>
                    <h4 style="font-size:14px;margin-bottom:10px;">Chronological Timeline (${{hist.length}} events)</h4>
                    <div style="max-height:300px;overflow-y:auto;">${{histHtml}}</div>
                `;
            }} catch (err) {{
                modalBody.innerHTML = "<p style='color:#ef4444;'>Error loading user details: " + err.message + "</p>";
            }}
        }}

        function closeUserModal() {{
            document.getElementById("userModal").style.display = "none";
        }}

        async function resetUser(phone) {{
            if (!confirm("Are you sure you want to reset all progress for " + phone + "?")) return;
            try {{
                const resp = await fetch("/admin/api/user/" + encodeURIComponent(phone) + "/reset", {{ method: "POST" }});
                if (resp.ok) {{
                    alert("User " + phone + " progress has been reset.");
                    location.reload();
                }} else {{
                    alert("Failed to reset user.");
                }}
            }} catch (e) {{
                alert("Error: " + e.message);
            }}
        }}

        window.onclick = function(event) {{
            const modal = document.getElementById("userModal");
            if (event.target == modal) closeUserModal();
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html)


# Top-level fallback for admin mounted app
app = router
