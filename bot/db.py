"""
bot/db.py

Persistent storage and analytics engine for the WhatsApp Learning Bot.
Saves users by their actual phone number (wa_id) and tracks learning activity.

Supported Backends:
1. SQLite (built-in sqlite3) - persists to data/portal.db (or /tmp/portal.db in serverless)
2. PostgreSQL / Supabase / Neon - via DATABASE_URL / POSTGRES_URL
3. Upstash Redis / Vercel KV - via UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (HTTP REST via httpx)
4. JSON file backup - data/users.json
"""

import copy
from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("whatsapp_bot")

# --- Configuration & Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, "tmp")
SYSTEM_TMP = os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"

SQLITE_PATH = (
    os.getenv("DATABASE_PATH")
    or os.getenv("SQLITE_PATH")
    or os.path.join(DATA_DIR, "portal.db")
)
FALLBACK_SQLITE_PATH = os.path.join(SYSTEM_TMP, "portal.db")

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("SUPABASE_DB_URL")
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN")

# JSON File Backups
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TMP_USERS_FILE = os.path.join(TMP_DIR, "users.json")
SYSTEM_TMP_USERS_FILE = os.path.join(SYSTEM_TMP, "whatsapp_bot_users.json") if SYSTEM_TMP else None

# In-memory fast cache
_MEMORY_CACHE: Dict[str, dict] = {}
_ACTIVE_BACKEND: str = "sqlite"
_DB_INITIALIZED: bool = False


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_utc_now_iso() -> str:
    return _get_utc_now().isoformat()


def _ensure_dirs() -> None:
    for d in (DATA_DIR, TMP_DIR):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


def _get_sqlite_connection() -> sqlite3.Connection:
    _ensure_dirs()
    target_path = SQLITE_PATH
    try:
        dir_name = os.path.dirname(target_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        conn = sqlite3.connect(target_path, timeout=10.0)
        conn.execute("CREATE TABLE IF NOT EXISTS _test_write (id INT)")
        conn.commit()
        return conn
    except Exception as e:
        logger.warning(f"Could not use primary SQLite path {target_path}: {e}. Falling back to {FALLBACK_SQLITE_PATH}")
        try:
            os.makedirs(os.path.dirname(FALLBACK_SQLITE_PATH), exist_ok=True)
            return sqlite3.connect(FALLBACK_SQLITE_PATH, timeout=10.0)
        except Exception as e2:
            logger.error(f"Failed to connect to fallback SQLite: {e2}")
            return sqlite3.connect(":memory:", timeout=10.0)


def init_db() -> str:
    """Initialize database tables and backend. Safe to call multiple times."""
    global _ACTIVE_BACKEND, _DB_INITIALIZED
    if _DB_INITIALIZED:
        return _ACTIVE_BACKEND

    try:
        conn = _get_sqlite_connection()
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    phone_number TEXT PRIMARY KEY,
                    phase TEXT DEFAULT 'idle',
                    unit_id TEXT,
                    lesson_index INTEGER,
                    completed_lessons TEXT DEFAULT '[]',
                    quiz_answers TEXT DEFAULT '{}',
                    assessment_answers TEXT DEFAULT '{}',
                    tutor_history TEXT DEFAULT '[]',
                    state_json TEXT,
                    created_at TEXT,
                    last_seen TEXT,
                    total_messages INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    hour_of_day INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_phone ON activity_logs (phone_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_time ON activity_logs (timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_hour ON activity_logs (hour_of_day)")
        conn.close()
        _ACTIVE_BACKEND = "sqlite"
        _DB_INITIALIZED = True
        logger.info(f"Database initialized successfully with SQLite at {SQLITE_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite: {e}", exc_info=True)
        _ACTIVE_BACKEND = "memory/json"

    # Migrate any legacy users from JSON if SQLite is empty
    _migrate_legacy_json()

    return _ACTIVE_BACKEND


def _migrate_legacy_json() -> None:
    """Imports any existing data/users.json into SQLite on first startup."""
    try:
        legacy_users = {}
        for path in (USERS_FILE,):
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        users = data.get("users") if isinstance(data.get("users"), dict) else data
                        if isinstance(users, dict):
                            legacy_users.update(users)
                except Exception:
                    pass

        if not legacy_users:
            return

        conn = _get_sqlite_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            if count == 0 and legacy_users:
                logger.info(f"Migrating {len(legacy_users)} legacy users from JSON into database...")
                for phone, st in legacy_users.items():
                    if not isinstance(st, dict):
                        continue
                    phase = st.get("phase", "idle")
                    unit_id = st.get("unit_id")
                    lesson_idx = st.get("lesson_index")
                    completed = json.dumps(st.get("completed_lessons") or [])
                    quizzes = json.dumps(st.get("quiz_answers") or {})
                    assessment = json.dumps(st.get("assessment_answers") or {})
                    tutor = json.dumps(st.get("tutor_history") or [])
                    created_at = st.get("created_at") or _get_utc_now_iso()
                    last_seen = st.get("last_seen") or created_at
                    total_msg = st.get("total_messages", 1)
                    raw_json = json.dumps(st)

                    cursor.execute("""
                        INSERT OR REPLACE INTO users (
                            phone_number, phase, unit_id, lesson_index,
                            completed_lessons, quiz_answers, assessment_answers,
                            tutor_history, state_json, created_at, last_seen, total_messages
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(phone), phase, unit_id, lesson_idx,
                        completed, quizzes, assessment,
                        tutor, raw_json, created_at, last_seen, total_msg
                    ))
        conn.close()
    except Exception as e:
        logger.warning(f"Legacy JSON migration error: {e}")


def _save_json_backup(all_users: dict) -> None:
    """Best-effort atomic write to users.json for safety and offline inspection."""
    _ensure_dirs()
    for candidate in (USERS_FILE, TMP_USERS_FILE, SYSTEM_TMP_USERS_FILE):
        if not candidate:
            continue
        try:
            os.makedirs(os.path.dirname(candidate), exist_ok=True)
            tmp = candidate + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"users": all_users, "updated_at": _get_utc_now_iso()}, f, ensure_ascii=False, indent=2)
            os.replace(tmp, candidate)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# User Data Access Methods
# ---------------------------------------------------------------------------

def get_user_state(phone_number: str) -> Optional[dict]:
    """Retrieve full state dict for a user by phone number."""
    init_db()
    clean_phone = str(phone_number).strip()
    if not clean_phone:
        return None

    if clean_phone in _MEMORY_CACHE:
        return copy.deepcopy(_MEMORY_CACHE[clean_phone])

    try:
        conn = _get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT state_json, phase, unit_id, lesson_index, completed_lessons, quiz_answers, assessment_answers, created_at, last_seen, total_messages FROM users WHERE phone_number = ?", (clean_phone,))
        row = cursor.fetchone()
        conn.close()

        if row:
            state_json, phase, unit_id, lesson_idx, completed_raw, quiz_raw, assess_raw, created_at, last_seen, total_msg = row
            st = {}
            if state_json:
                try:
                    st = json.loads(state_json)
                except Exception:
                    st = {}
            st["phone_number"] = clean_phone
            st["phase"] = phase or st.get("phase", "idle")
            st["unit_id"] = unit_id or st.get("unit_id")
            st["lesson_index"] = lesson_idx if lesson_idx is not None else st.get("lesson_index")
            try:
                st["completed_lessons"] = json.loads(completed_raw) if completed_raw else st.get("completed_lessons", [])
            except Exception:
                st["completed_lessons"] = st.get("completed_lessons", [])
            try:
                st["quiz_answers"] = json.loads(quiz_raw) if quiz_raw else st.get("quiz_answers", {})
            except Exception:
                st["quiz_answers"] = st.get("quiz_answers", {})
            try:
                st["assessment_answers"] = json.loads(assess_raw) if assess_raw else st.get("assessment_answers", {})
            except Exception:
                st["assessment_answers"] = st.get("assessment_answers", {})
            st["created_at"] = created_at or st.get("created_at") or _get_utc_now_iso()
            st["last_seen"] = last_seen or st.get("last_seen") or _get_utc_now_iso()
            st["total_messages"] = total_msg or st.get("total_messages", 0)

            _MEMORY_CACHE[clean_phone] = st
            return copy.deepcopy(st)
    except Exception as e:
        logger.error(f"Error reading user {clean_phone} from SQLite: {e}")

    return None


def save_user_state(phone_number: str, state_dict: dict) -> None:
    """Save or update user state in the database."""
    init_db()
    clean_phone = str(phone_number).strip()
    if not clean_phone:
        return

    now_iso = _get_utc_now_iso()
    state = copy.deepcopy(state_dict)

    if "created_at" not in state or not state["created_at"]:
        state["created_at"] = now_iso
    state["last_seen"] = now_iso
    state["phone_number"] = clean_phone
    state["total_messages"] = state.get("total_messages", 0) + 1

    _MEMORY_CACHE[clean_phone] = copy.deepcopy(state)

    phase = state.get("phase", "idle")
    unit_id = state.get("unit_id")
    lesson_idx = state.get("lesson_index")
    completed = json.dumps(state.get("completed_lessons") or [])
    quiz_ans = json.dumps(state.get("quiz_answers") or {})
    assess_ans = json.dumps(state.get("assessment_answers") or {})
    tutor_hist = json.dumps(state.get("tutor_history") or [])
    raw_json = json.dumps(state, ensure_ascii=False)
    created_at = state.get("created_at")
    last_seen = state.get("last_seen")
    total_msg = state.get("total_messages", 1)

    try:
        conn = _get_sqlite_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO users (
                    phone_number, phase, unit_id, lesson_index,
                    completed_lessons, quiz_answers, assessment_answers,
                    tutor_history, state_json, created_at, last_seen, total_messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clean_phone, phase, unit_id, lesson_idx,
                completed, quiz_ans, assess_ans,
                tutor_hist, raw_json, created_at, last_seen, total_msg
            ))
        conn.close()
    except Exception as e:
        logger.error(f"Failed to save user {clean_phone} to SQLite: {e}")

    try:
        _save_json_backup(_MEMORY_CACHE)
    except Exception:
        pass


def delete_user(phone_number: str) -> bool:
    """Delete a user and their activity from the database."""
    init_db()
    clean_phone = str(phone_number).strip()
    _MEMORY_CACHE.pop(clean_phone, None)

    try:
        conn = _get_sqlite_connection()
        with conn:
            conn.execute("DELETE FROM users WHERE phone_number = ?", (clean_phone,))
            conn.execute("DELETE FROM activity_logs WHERE phone_number = ?", (clean_phone,))
        conn.close()
        _save_json_backup(_MEMORY_CACHE)
        return True
    except Exception as e:
        logger.error(f"Error deleting user {clean_phone}: {e}")
        return False


def get_all_users() -> Dict[str, dict]:
    """Return all users mapped by phone_number."""
    init_db()
    users: Dict[str, dict] = {}
    try:
        conn = _get_sqlite_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT phone_number, state_json, phase, unit_id, lesson_index, completed_lessons, quiz_answers, assessment_answers, created_at, last_seen, total_messages FROM users")
        for row in cursor.fetchall():
            phone, state_json, phase, unit_id, lesson_idx, completed_raw, quiz_raw, assess_raw, created_at, last_seen, total_msg = row
            st = {}
            if state_json:
                try:
                    st = json.loads(state_json)
                except Exception:
                    st = {}
            st["phone_number"] = phone
            st["phase"] = phase or st.get("phase", "idle")
            st["unit_id"] = unit_id or st.get("unit_id")
            st["lesson_index"] = lesson_idx if lesson_idx is not None else st.get("lesson_index")
            try:
                st["completed_lessons"] = json.loads(completed_raw) if completed_raw else st.get("completed_lessons", [])
            except Exception:
                st["completed_lessons"] = st.get("completed_lessons", [])
            try:
                st["quiz_answers"] = json.loads(quiz_raw) if quiz_raw else st.get("quiz_answers", {})
            except Exception:
                st["quiz_answers"] = st.get("quiz_answers", {})
            try:
                st["assessment_answers"] = json.loads(assess_raw) if assess_raw else st.get("assessment_answers", {})
            except Exception:
                st["assessment_answers"] = st.get("assessment_answers", {})
            st["created_at"] = created_at or st.get("created_at")
            st["last_seen"] = last_seen or st.get("last_seen")
            st["total_messages"] = total_msg or st.get("total_messages", 0)

            users[phone] = st
            _MEMORY_CACHE[phone] = st
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching all users from SQLite: {e}")
        return copy.deepcopy(_MEMORY_CACHE)

    return copy.deepcopy(users)


# ---------------------------------------------------------------------------
# Activity & Analytics Logging ("When are they learning?")
# ---------------------------------------------------------------------------

def log_activity(phone_number: str, event_type: str, details: str = "") -> None:
    """
    Log a learning activity event with precise UTC timestamp, hour, and day.
    Tracks exact times when users are learning.
    """
    init_db()
    clean_phone = str(phone_number).strip()
    now = _get_utc_now()
    now_iso = now.isoformat()
    hour = now.hour
    day = now.weekday()  # 0=Monday, 6=Sunday

    try:
        conn = _get_sqlite_connection()
        with conn:
            conn.execute("""
                INSERT INTO activity_logs (phone_number, event_type, details, timestamp, hour_of_day, day_of_week)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (clean_phone, event_type, details, now_iso, hour, day))
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to log activity for {clean_phone}: {e}")


def get_activity_logs(limit: int = 50, phone_number: Optional[str] = None) -> List[dict]:
    """Retrieve recent activity logs, optionally filtered by phone number."""
    init_db()
    logs = []
    try:
        conn = _get_sqlite_connection()
        cursor = conn.cursor()
        if phone_number:
            cursor.execute("""
                SELECT id, phone_number, event_type, details, timestamp, hour_of_day, day_of_week
                FROM activity_logs
                WHERE phone_number = ?
                ORDER BY id DESC LIMIT ?
            """, (str(phone_number).strip(), limit))
        else:
            cursor.execute("""
                SELECT id, phone_number, event_type, details, timestamp, hour_of_day, day_of_week
                FROM activity_logs
                ORDER BY id DESC LIMIT ?
            """, (limit,))
        for row in cursor.fetchall():
            logs.append({
                "id": row[0],
                "phone_number": row[1],
                "event_type": row[2],
                "details": row[3],
                "timestamp": row[4],
                "hour_of_day": row[5],
                "day_of_week": row[6],
            })
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching activity logs: {e}")
    return logs


def get_analytics_summary() -> dict:
    """
    Compute comprehensive analytics from actual real database records:
    - User totals (total, active, completed, assessment)
    - "When are they learning?" Hourly distribution (0-23 hours)
    - "When are they learning?" Days of week & daily trends
    - Learner status breakdown (Pie / Donut chart)
    - Time-of-day learning breakdown (Pie / Donut chart)
    - 11-Module progression funnel
    - Assessment response insights
    - Recent activity feed
    """
    init_db()
    all_users = get_all_users()
    total_users = len(all_users)

    active_learners = 0
    completed_learners = 0
    assessment_completed = 0
    total_interactions = 0

    status_distribution = {
        "completed": 0,
        "lesson": 0,
        "quiz": 0,
        "tutor": 0,
        "assessment": 0,
        "idle": 0,
    }

    # Funnel per lesson index (0 to 10 for 11 lessons)
    lesson_funnel = [0] * 11

    # Format user rows
    users_list = []
    for phone, u in all_users.items():
        phase = u.get("phase", "idle")
        lesson_idx = u.get("lesson_index")
        completed_lessons = u.get("completed_lessons") or []
        assess_answers = u.get("assessment_answers") or {}
        quiz_answers = u.get("quiz_answers") or {}
        msg_count = u.get("total_messages", 0)
        total_interactions += msg_count

        if phase == "complete" or len(completed_lessons) >= 11:
            completed_learners += 1
            status_distribution["completed"] += 1
            progress_pct = 100
        elif phase == "lesson":
            active_learners += 1
            status_distribution["lesson"] += 1
            curr_idx = lesson_idx if lesson_idx is not None else 0
            progress_pct = min(100, round((curr_idx / 11) * 100))
            if 0 <= curr_idx < 11:
                lesson_funnel[curr_idx] += 1
        elif phase == "quiz":
            active_learners += 1
            status_distribution["quiz"] += 1
            curr_idx = lesson_idx if lesson_idx is not None else 0
            progress_pct = min(100, round((curr_idx / 11) * 100))
            if 0 <= curr_idx < 11:
                lesson_funnel[curr_idx] += 1
        elif phase == "tutor":
            active_learners += 1
            status_distribution["tutor"] += 1
            curr_idx = lesson_idx if lesson_idx is not None else 0
            progress_pct = min(100, round((curr_idx / 11) * 100))
            if 0 <= curr_idx < 11:
                lesson_funnel[curr_idx] += 1
        elif phase == "assessment":
            status_distribution["assessment"] += 1
            progress_pct = 0
        else:
            status_distribution["idle"] += 1
            progress_pct = 0

        if assess_answers and len(assess_answers) >= 4:
            assessment_completed += 1

        last_seen = u.get("last_seen") or u.get("created_at") or ""
        created_at = u.get("created_at") or ""
        relative_last_seen = _format_relative_time(last_seen)

        current_module_title = f"Module {(lesson_idx + 1) if lesson_idx is not None else 1}"
        if phase == "complete":
            current_module_title = "Course Completed (11/11)"
        elif phase == "assessment":
            current_module_title = f"AI Self-Assessment ({len(assess_answers)}/4)"
        elif phase == "idle":
            current_module_title = "Not started"

        users_list.append({
            "phone_number": phone,
            "phase": phase,
            "lesson_index": lesson_idx,
            "progress_percent": progress_pct,
            "current_module_title": current_module_title,
            "completed_lessons_count": len(completed_lessons),
            "quiz_answers_count": len(quiz_answers),
            "assessment_answers": assess_answers,
            "created_at": created_at,
            "last_seen": last_seen,
            "last_seen_relative": relative_last_seen,
            "total_messages": msg_count,
        })

    # Sort users by last_seen descending
    users_list.sort(key=lambda x: x.get("last_seen") or "", reverse=True)

    # Hourly learning activity (0-23)
    hourly_counts = [0] * 24
    day_counts = [0] * 7  # 0=Mon, 6=Sun

    try:
        conn = _get_sqlite_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT hour_of_day, COUNT(*) FROM activity_logs GROUP BY hour_of_day")
        for h, count in cursor.fetchall():
            if 0 <= h < 24:
                hourly_counts[h] = count

        cursor.execute("SELECT day_of_week, COUNT(*) FROM activity_logs GROUP BY day_of_week")
        for d, count in cursor.fetchall():
            if 0 <= d < 7:
                day_counts[d] = count

        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        logged_events_count = cursor.fetchone()[0]
        if logged_events_count > 0:
            total_interactions = max(total_interactions, logged_events_count)

        conn.close()
    except Exception as e:
        logger.warning(f"Error calculating activity analytics: {e}")

    # Fetch last 40 activity items
    recent_activity = get_activity_logs(limit=40)

    # Time of day buckets
    morning = sum(hourly_counts[6:12])     # 6am - 12pm
    afternoon = sum(hourly_counts[12:17])  # 12pm - 5pm
    evening = sum(hourly_counts[17:22])    # 5pm - 10pm
    night = sum(hourly_counts[22:24]) + sum(hourly_counts[0:6])  # 10pm - 6am

    # Peak learning hour
    peak_hour = 0
    max_h_count = 0
    for h, c in enumerate(hourly_counts):
        if c > max_h_count:
            max_h_count = c
            peak_hour = h

    days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    daily_formatted = [{"day": days_labels[i], "count": day_counts[i]} for i in range(7)]

    # Assessment insights aggregation
    assessment_summary = {
        "ai_use": {"Never": 0, "Sometimes": 0, "Regularly": 0},
        "comfort": {"Not confident": 0, "Somewhat confident": 0, "Very confident": 0},
        "challenge": {"Don't know where to start": 0, "Limited access/internet": 0, "Worried about misuse": 0},
        "goal": {"Practical lesson ideas": 0, "Time-saving tools": 0, "Responsible & safe AI": 0},
    }
    for u in all_users.values():
        ans = u.get("assessment_answers") or {}
        if ans.get("ai_use") == "A":
            assessment_summary["ai_use"]["Never"] += 1
        elif ans.get("ai_use") == "B":
            assessment_summary["ai_use"]["Sometimes"] += 1
        elif ans.get("ai_use") == "C":
            assessment_summary["ai_use"]["Regularly"] += 1

        if ans.get("comfort") == "A":
            assessment_summary["comfort"]["Not confident"] += 1
        elif ans.get("comfort") == "B":
            assessment_summary["comfort"]["Somewhat confident"] += 1
        elif ans.get("comfort") == "C":
            assessment_summary["comfort"]["Very confident"] += 1

        if ans.get("challenge") == "A":
            assessment_summary["challenge"]["Don't know where to start"] += 1
        elif ans.get("challenge") == "B":
            assessment_summary["challenge"]["Limited access/internet"] += 1
        elif ans.get("challenge") == "C":
            assessment_summary["challenge"]["Worried about misuse"] += 1

        if ans.get("goal") == "A":
            assessment_summary["goal"]["Practical lesson ideas"] += 1
        elif ans.get("goal") == "B":
            assessment_summary["goal"]["Time-saving tools"] += 1
        elif ans.get("goal") == "C":
            assessment_summary["goal"]["Responsible & safe AI"] += 1

    completion_rate = round((completed_learners / total_users * 100), 1) if total_users > 0 else 0
    avg_progress = round(sum(u["progress_percent"] for u in users_list) / total_users, 1) if total_users > 0 else 0

    return {
        "status": "ok",
        "backend": _ACTIVE_BACKEND,
        "database_path": SQLITE_PATH,
        "summary": {
            "total_users": total_users,
            "active_learners": active_learners,
            "completed_learners": completed_learners,
            "assessment_completed": assessment_completed,
            "total_interactions": total_interactions,
            "completion_rate": completion_rate,
            "average_progress": avg_progress,
            "peak_hour_utc": f"{peak_hour:02d}:00 UTC",
            "peak_hour_count": max_h_count,
        },
        "status_distribution": {
            "labels": ["Course Completed", "Learning Lessons", "Taking Quiz", "AI Tutor Mode", "AI Self-Assessment", "Idle / Menu"],
            "counts": [
                status_distribution["completed"],
                status_distribution["lesson"],
                status_distribution["quiz"],
                status_distribution["tutor"],
                status_distribution["assessment"],
                status_distribution["idle"],
            ],
            "raw": status_distribution,
        },
        "when_are_they_learning": {
            "hourly_counts": hourly_counts,
            "hourly_labels": [f"{h:02d}:00" for h in range(24)],
            "time_of_day": {
                "Morning (06:00 - 12:00)": morning,
                "Afternoon (12:00 - 17:00)": afternoon,
                "Evening (17:00 - 22:00)": evening,
                "Night (22:00 - 06:00)": night,
            },
            "time_of_day_counts": [morning, afternoon, evening, night],
            "time_of_day_labels": ["Morning (06:00 - 12:00)", "Afternoon (12:00 - 17:00)", "Evening (17:00 - 22:00)", "Night (22:00 - 06:00)"],
            "daily_counts": daily_formatted,
        },
        "progression_funnel": {
            "lesson_counts": lesson_funnel,
            "labels": [f"Mod {i+1}" for i in range(11)],
            "total_modules": 11,
        },
        "assessment_insights": assessment_summary,
        "users": users_list,
        "recent_activity": recent_activity,
    }


def _format_relative_time(iso_str: str) -> str:
    """Helper to convert ISO UTC timestamp to human-friendly relative string."""
    if not iso_str:
        return "Never"
    try:
        clean_iso = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        diff = _get_utc_now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 0:
            return "Just now"
        if seconds < 60:
            return f"{seconds}s ago"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days == 1:
            return "Yesterday"
        if days < 30:
            return f"{days}d ago"
        return dt.strftime("%b %d, %Y")
    except Exception:
        return iso_str[:16]
