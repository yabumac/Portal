"""
api/admin.py - Admin dashboard for viewing users and their progress.
"""

import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot import state

app = FastAPI()


ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")


@app.get("/")
@app.get("/admin")
async def admin_dashboard(request: Request):
    # Basic auth via query param or just open if no password set differently
    password = request.query_params.get("password") or request.query_params.get("pass")
    if ADMIN_PASSWORD and password != ADMIN_PASSWORD:
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Admin Login</title><meta name="viewport" content="width=device-width, initial-scale=1"></head>
        <body style="font-family:sans-serif;max-width:400px;margin:40px auto;">
            <h2>Admin Login</h2>
            <form method="get">
                <input type="password" name="password" placeholder="Password" style="width:100%;padding:8px;">
                <button type="submit" style="margin-top:10px;padding:8px 16px;">Login</button>
            </form>
        </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=401)
    
    users = state.get_all_users()
    
    # Build summary
    rows = []
    for wa_id, s in users.items():
        phase = s.get("phase", "unknown")
        unit = s.get("unit_id") or "-"
        lesson_idx = s.get("lesson_index")
        lesson_info = "-"
        if lesson_idx is not None and unit:
            try:
                from content import curriculum
                lessons = curriculum.list_lessons(unit)
                if lesson_idx < len(lessons):
                    lesson_info = f"{lesson_idx+1}/{len(lessons)} ({lessons[lesson_idx]})"
            except:
                pass
        rows.append({
            "wa_id": wa_id,
            "phase": phase,
            "unit": unit,
            "lesson": lesson_info,
            "assessment_answers": s.get("assessment_answers") or {},
            "raw": s
        })
    
    rows_html = ""
    for r in rows:
        rows_html += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;font-family:monospace;">{r['wa_id']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{r['phase']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{r['unit']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{r['lesson']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{json.dumps(r['assessment_answers'])}</td>
            <td style="padding:8px;border:1px solid #ddd;"><a href="?password={password or ''}&view={r['wa_id']}">View</a> | <a href="?password={password or ''}&reset={r['wa_id']}">Reset</a></td>
        </tr>
        """
    
    # Handle reset
    reset_id = request.query_params.get("reset")
    if reset_id and password == ADMIN_PASSWORD:
        try:
            state.reset(reset_id)
            return HTMLResponse(content=f"<script>window.location='?password={password}';</script>")
        except:
            pass
    
    # Handle view
    view_id = request.query_params.get("view")
    detail_html = ""
    if view_id and view_id in users:
        detail_html = f"""
        <h3>Details for {view_id}</h3>
        <pre style="background:#f5f5f5;padding:10px;overflow:auto;">{json.dumps(users[view_id], indent=2)}</pre>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Portal Admin Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th {{ background:#f0f0f0; padding:8px; border:1px solid #ddd; text-align:left; }}
        </style>
    </head>
    <body>
        <h1>EdTech Hub - User Progress Dashboard</h1>
        <p>Total users: {len(rows)}</p>
        {detail_html}
        <table>
            <thead>
                <tr>
                    <th>Phone/WA ID</th>
                    <th>Phase</th>
                    <th>Unit</th>
                    <th>Lesson Progress</th>
                    <th>Assessment</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <p style="margin-top:20px;color:#666;">Data stored in data/users.json</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/users")
async def api_users(request: Request):
    password = request.query_params.get("password") or request.headers.get("x-admin-password")
    if ADMIN_PASSWORD and password != ADMIN_PASSWORD:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return JSONResponse(state.get_all_users())
