"""
bot/db.py

Persistent storage and analytics engine for the WhatsApp Learning Bot.
Saves users by their actual phone number (wa_id) and tracks learning activity.

Supported Backends:
1. Upstash Redis / Vercel KV - via UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (HTTP REST via httpx)
2. PostgreSQL / Supabase / Neon - via DATABASE_URL / POSTGRES_URL
3. SQLite (built-in sqlite3) - persists to data/portal.db (or /tmp/portal.db in serverless)
"""

import copy
from datetime import datetime, timezone
import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("whatsapp_bot")

# --- Configuration & Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TMP_DIR = os.path.join(BASE_DIR, "tmp")
SYSTEM_TMP = os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"

SQLITE_PATH = (
    os.getenv("DATABASE_PATH")
    or os.getenv("SQLITE_PATH")
    or (os.path.join(SYSTEM_TMP, "portal.db") if os.environ.get("VERCEL") else os.path.join(DATA_DIR, "portal.db"))
)
FALLBACK_SQLITE_PATH = os.path.join(SYSTEM_TMP, "portal.db")

DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("SUPABASE_DB_URL")


def _get_upstash_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Resolve Upstash URL and Token across all common Vercel prefix variations."""
    url = (
        os.getenv("UPSTASH_REDIS_REST_URL")
        or os.getenv("KV_REST_API_URL")
        or os.getenv("STORAGE_REST_API_URL")
        or os.getenv("STORAGE_URL")
        or os.getenv("REDIS_REST_API_URL")
        or os.getenv("UPSTASH_URL")
    )
    token = (
        os.getenv("UPSTASH_REDIS_REST_TOKEN")
        or os.getenv("KV_REST_API_TOKEN")
        or os.getenv("STORAGE_REST_API_TOKEN")
        or os.getenv("STORAGE_TOKEN")
        or os.getenv("REDIS_REST_API_TOKEN")
        or os.getenv("UPSTASH_TOKEN")
    )
    if url and token:
        return url, token

    # Auto-detect ANY custom prefix (e.g. [PREFIX]_REST_API_URL / [PREFIX]_REST_API_TOKEN)
    for k, v in os.environ.items():
        if k.endswith("_REST_API_URL") and v:
            prefix = k[:-len("_REST_API_URL")]
            tok = os.environ.get(f"{prefix}_REST_API_TOKEN")
            if tok:
                return v, tok
    return url, token


def _is_upstash_configured() -> bool:
    url, token = _get_upstash_credentials()
    return bool(url and token)


def _upstash_exec(command: list) -> Any:
    """Execute a single Redis command via Upstash REST API."""
    url, token = _get_upstash_credentials()
    if not (url and token):
        raise RuntimeError("Upstash is not configured")

    clean_url = url.rstrip("/")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    with httpx.Client(timeout=8.0) as client:
        resp = client.post(clean_url, headers=headers, json=command)
        if resp.status_code == 200:
            return resp.json().get("result")
        raise RuntimeError(f"Upstash API error {resp.status_code}: {resp.text}")

# JSON File Backups
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TMP_USERS_FILE = os.path.join(TMP_DIR, "users.json")
SYSTEM_TMP_USERS_FILE = os.path.join(SYSTEM_TMP, "whatsapp_bot_users.json") if SYSTEM_TMP else None

# In-memory fast cache
_MEMORY_CACHE: Dict[str, dict] = {}
_ACTIVE_BACKEND: str = "sqlite"
_ACTIVE_SQLITE_PATH: str = SQLITE_PATH
_DB_INITIALIZED: bool = False


def _format_relative_time(iso_str: str) -> str:
    """Format an ISO timestamp to human-readable relative time string."""
    if not iso_str:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        diff = _get_utc_now() - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        elif secs < 3600:
            return f"{secs // 60}m ago"
        elif secs < 86400:
            return f"{secs // 3600}h ago"
        else:
            return f"{secs // 86400}d ago"
    except Exception:
        return iso_str[:16].replace("T", " ")


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





# ---------------------------------------------------------------------------
# SQLite Client (Built-in)
# ---------------------------------------------------------------------------

def _get_sqlite_connection() -> sqlite3.Connection:
    global _ACTIVE_SQLITE_PATH
    target_path = _ACTIVE_SQLITE_PATH or SQLITE_PATH
    try:
        dir_name = os.path.dirname(target_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        conn = sqlite3.connect(target_path, timeout=15.0)
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn
    except Exception as e:
        logger.warning(f"Could not connect to {target_path}: {e}. Falling back to {FALLBACK_SQLITE_PATH}")
        try:
            _ACTIVE_SQLITE_PATH = FALLBACK_SQLITE_PATH
            os.makedirs(os.path.dirname(FALLBACK_SQLITE_PATH), exist_ok=True)
            conn = sqlite3.connect(FALLBACK_SQLITE_PATH, timeout=15.0)
            conn.execute("PRAGMA busy_timeout = 10000")
            return conn
        except Exception as e2:
            logger.error(f"Failed to connect to fallback SQLite: {e2}")
            _ACTIVE_SQLITE_PATH = ":memory:"
            return sqlite3.connect(":memory:", timeout=15.0)


def init_db() -> str:
    """Initialize database tables and backend. Safe to call multiple times."""
    global _ACTIVE_BACKEND, _ACTIVE_SQLITE_PATH, _DB_INITIALIZED
    if _DB_INITIALIZED:
        return _ACTIVE_BACKEND

    # 1. Try Upstash Redis if configured
    if _is_upstash_configured():
        try:
            res = _upstash_exec(["PING"])
            if res == "PONG":
                _ACTIVE_BACKEND = "upstash_redis"
                _DB_INITIALIZED = True
                logger.info("Database initialized successfully with Upstash Redis REST")
                return _ACTIVE_BACKEND
        except Exception as upstash_err:
            logger.warning(f"Failed to connect to Upstash Redis: {upstash_err}. Falling back to SQLite.")

    # 2. Try PostgreSQL if configured and driver available
    if DATABASE_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        phone_number VARCHAR(64) PRIMARY KEY,
                        phase VARCHAR(32) DEFAULT 'idle',
                        unit_id VARCHAR(64),
                        lesson_index INT,
                        completed_lessons TEXT DEFAULT '[]',
                        quiz_answers TEXT DEFAULT '{}',
                        assessment_answers TEXT DEFAULT '{}',
                        tutor_history TEXT DEFAULT '[]',
                        state_json TEXT,
                        created_at VARCHAR(64),
                        last_seen VARCHAR(64),
                        total_messages INT DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS activity_logs (
                        id SERIAL PRIMARY KEY,
                        phone_number VARCHAR(64) NOT NULL,
                        event_type VARCHAR(64) NOT NULL,
                        details TEXT,
                        timestamp VARCHAR(64) NOT NULL,
                        hour_of_day INT NOT NULL,
                        day_of_week INT NOT NULL
                    );
                """)
                conn.commit()
            conn.close()
            _ACTIVE_BACKEND = "postgresql"
            _DB_INITIALIZED = True
            logger.info("Database initialized successfully with PostgreSQL")
            return _ACTIVE_BACKEND
        except Exception as pg_err:
            logger.warning(f"PostgreSQL connection failed ({pg_err}), falling back to SQLite.")

    # 3. SQLite setup
    try:
        _ensure_dirs()
        dir_name = os.path.dirname(SQLITE_PATH)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        test_conn = sqlite3.connect(SQLITE_PATH, timeout=5.0)
        test_conn.execute("CREATE TABLE IF NOT EXISTS _schema_version (version INT)")
        test_conn.commit()
        test_conn.close()
        _ACTIVE_SQLITE_PATH = SQLITE_PATH
    except Exception as write_err:
        logger.info(f"Primary SQLite path {SQLITE_PATH} not writable ({write_err}). Using {FALLBACK_SQLITE_PATH}")
        _ACTIVE_SQLITE_PATH = FALLBACK_SQLITE_PATH

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
        logger.info(f"Database initialized successfully with SQLite at {_ACTIVE_SQLITE_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite: {e}", exc_info=True)
        _ACTIVE_BACKEND = "memory"

    return _ACTIVE_BACKEND


# ---------------------------------------------------------------------------
# User Data Access Methods
# ---------------------------------------------------------------------------

def get_user_state(phone_number: str) -> Optional[dict]:
    """Retrieve full state dict for a user by phone number."""
    init_db()
    clean_phone = str(phone_number).strip()
    if not clean_phone:
        return None

    # Upstash Redis check
    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            raw = _upstash_exec(["HGET", "edtech:users", clean_phone])
            if raw:
                st = json.loads(raw)
                st["phone_number"] = clean_phone
                _MEMORY_CACHE[clean_phone] = copy.deepcopy(st)
                return st
        except Exception as e:
            logger.error(f"Upstash HGET error for {clean_phone}: {e}")

    # Memory cache check
    if clean_phone in _MEMORY_CACHE:
        return copy.deepcopy(_MEMORY_CACHE[clean_phone])

    # SQLite read
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
    raw_json = json.dumps(state, ensure_ascii=False)

    # 1. Upstash Redis save
    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            _upstash_exec(["HSET", "edtech:users", clean_phone, raw_json])
        except Exception as e:
            logger.error(f"Failed to save user {clean_phone} to Upstash Redis: {e}")

    # 2. SQLite save (always maintain local sync if possible)
    phase = state.get("phase", "idle")
    unit_id = state.get("unit_id")
    lesson_idx = state.get("lesson_index")
    completed = json.dumps(state.get("completed_lessons") or [])
    quiz_ans = json.dumps(state.get("quiz_answers") or {})
    assess_ans = json.dumps(state.get("assessment_answers") or {})
    tutor_hist = json.dumps(state.get("tutor_history") or [])
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


def delete_user(phone_number: str) -> bool:
    """Delete a user and their activity from the database."""
    init_db()
    clean_phone = str(phone_number).strip()
    _MEMORY_CACHE.pop(clean_phone, None)

    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            _upstash_exec(["HDEL", "edtech:users", clean_phone])
        except Exception as e:
            logger.error(f"Upstash HDEL error for {clean_phone}: {e}")

    try:
        conn = _get_sqlite_connection()
        with conn:
            conn.execute("DELETE FROM users WHERE phone_number = ?", (clean_phone,))
            conn.execute("DELETE FROM activity_logs WHERE phone_number = ?", (clean_phone,))
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error deleting user {clean_phone}: {e}")
        return False


def get_all_users() -> Dict[str, dict]:
    """Return all users mapped by phone_number."""
    init_db()
    users: Dict[str, dict] = {}

    # 1. Upstash Redis
    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            raw_data = _upstash_exec(["HGETALL", "edtech:users"])
            if isinstance(raw_data, dict):
                for phone, val in raw_data.items():
                    try:
                        parsed = json.loads(val) if isinstance(val, str) else val
                        parsed["phone_number"] = phone
                        users[phone] = parsed
                        _MEMORY_CACHE[phone] = parsed
                    except Exception:
                        pass
                return copy.deepcopy(users)
            elif isinstance(raw_data, list):
                # Redis returns alternating [key1, val1, key2, val2, ...]
                for i in range(0, len(raw_data) - 1, 2):
                    phone = raw_data[i]
                    val = raw_data[i + 1]
                    try:
                        parsed = json.loads(val) if isinstance(val, str) else val
                        parsed["phone_number"] = phone
                        users[phone] = parsed
                        _MEMORY_CACHE[phone] = parsed
                    except Exception:
                        pass
                return copy.deepcopy(users)
        except Exception as e:
            logger.error(f"Upstash HGETALL error: {e}")

    # 2. SQLite
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
    """Log an activity event with precise UTC timestamp, hour, and day."""
    init_db()
    clean_phone = str(phone_number).strip()
    now = _get_utc_now()
    now_iso = now.isoformat()
    hour = now.hour
    day = now.weekday()  # 0=Monday, 6=Sunday

    log_entry = {
        "phone_number": clean_phone,
        "event_type": event_type,
        "details": details,
        "timestamp": now_iso,
        "hour_of_day": hour,
        "day_of_week": day,
    }

    # Upstash Redis list
    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            _upstash_exec(["LPUSH", "edtech:activity", json.dumps(log_entry)])
            _upstash_exec(["LTRIM", "edtech:activity", 0, 1999])
        except Exception as e:
            logger.warning(f"Upstash LPUSH log error: {e}")

    # SQLite
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
    logs: List[dict] = []

    # Upstash Redis
    if _ACTIVE_BACKEND == "upstash_redis":
        try:
            raw_entries = _upstash_exec(["LRANGE", "edtech:activity", 0, limit * 2]) or []
            for item in raw_entries:
                try:
                    entry = json.loads(item) if isinstance(item, str) else item
                    if phone_number and entry.get("phone_number") != str(phone_number).strip():
                        continue
                    logs.append(entry)
                    if len(logs) >= limit:
                        break
                except Exception:
                    pass
            return logs
        except Exception as e:
            logger.error(f"Upstash LRANGE error: {e}")

    # SQLite
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
    Compute comprehensive analytics from actual real database records.
    ZERO mock or sample data.
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

    total_mods = 7
    try:
        from content import curriculum
        total_mods = curriculum.total_lessons() or 7
    except Exception:
        pass

    lesson_funnel = [0] * total_mods

    users_list = []
    for phone, u in all_users.items():
        phase = u.get("phase", "idle")
        lesson_idx = u.get("lesson_index")
        completed_lessons = u.get("completed_lessons") or []
        assess_answers = u.get("assessment_answers") or {}
        quiz_answers = u.get("quiz_answers") or {}
        msg_count = u.get("total_messages", 0)
        total_interactions += msg_count

        if phase == "complete" or len(completed_lessons) >= total_mods:
            completed_learners += 1
            status_distribution["completed"] += 1
            progress_pct = 100
        elif phase in ("lesson", "quiz", "tutor"):
            active_learners += 1
            status_distribution[phase] += 1
            curr_idx = lesson_idx if lesson_idx is not None else 0
            progress_pct = min(100, round((curr_idx / total_mods) * 100))
            if 0 <= curr_idx < total_mods:
                lesson_funnel[curr_idx] += 1
        elif phase == "assessment":
            status_distribution["assessment"] += 1
            progress_pct = 5
        else:
            status_distribution["idle"] += 1
            progress_pct = 0

        if len(assess_answers) >= 4:
            assessment_completed += 1

        curr_title = f"Module {(lesson_idx or 0) + 1}"
        try:
            from content import curriculum
            mod = curriculum.get_lesson(curriculum.DEFAULT_UNIT_ID, lesson_idx or 0)
            if mod:
                curr_title = mod.get("title", curr_title)
        except Exception:
            pass

        last_seen = u.get("last_seen", "")
        rel_time = "Never"
        if last_seen:
            try:
                dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                diff = _get_utc_now() - dt
                secs = int(diff.total_seconds())
                if secs < 60:
                    rel_time = f"{secs}s ago"
                elif secs < 3600:
                    rel_time = f"{secs // 60}m ago"
                elif secs < 86400:
                    rel_time = f"{secs // 3600}h ago"
                else:
                    rel_time = f"{secs // 86400}d ago"
            except Exception:
                rel_time = last_seen[:10]

        users_list.append({
            "phone_number": phone,
            "phase": phase,
            "lesson_index": lesson_idx,
            "current_module_title": curr_title,
            "progress_percent": progress_pct,
            "completed_count": len(completed_lessons),
            "total_messages": msg_count,
            "last_seen": last_seen,
            "last_seen_relative": rel_time,
            "assessment_answers": assess_answers,
            "quiz_answers": quiz_answers,
            "created_at": u.get("created_at", ""),
        })

    users_list.sort(key=lambda x: x.get("last_seen", ""), reverse=True)

    # Activity by hour & day of week
    hourly_distribution = [0] * 24
    daily_distribution = [0] * 7
    all_logs = get_activity_logs(limit=500)
    for log in all_logs:
        h = log.get("hour_of_day")
        if h is not None and 0 <= h < 24:
            hourly_distribution[h] += 1
        d = log.get("day_of_week")
        if d is not None and 0 <= d < 7:
            daily_distribution[d] += 1

    time_of_day_slots = {
        "Morning (06:00 - 12:00)": sum(hourly_distribution[6:12]),
        "Afternoon (12:00 - 18:00)": sum(hourly_distribution[12:18]),
        "Evening (18:00 - 23:00)": sum(hourly_distribution[18:23]),
        "Night (23:00 - 06:00)": hourly_distribution[23] + sum(hourly_distribution[0:6]),
    }

    # Assessment insights
    survey_stats = {
        "q1_ai_use": {"A": 0, "B": 0, "C": 0},
        "q2_comfort": {"A": 0, "B": 0, "C": 0},
        "q3_challenge": {"A": 0, "B": 0, "C": 0},
        "q4_goal": {"A": 0, "B": 0, "C": 0},
    }
    for u in all_users.values():
        ans = u.get("assessment_answers") or {}
        if ans.get("ai_use") in survey_stats["q1_ai_use"]:
            survey_stats["q1_ai_use"][ans["ai_use"]] += 1
        if ans.get("comfort") in survey_stats["q2_comfort"]:
            survey_stats["q2_comfort"][ans["comfort"]] += 1
        if ans.get("challenge") in survey_stats["q3_challenge"]:
            survey_stats["q3_challenge"][ans["challenge"]] += 1
        if ans.get("goal") in survey_stats["q4_goal"]:
            survey_stats["q4_goal"][ans["goal"]] += 1

    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    is_ephemeral = is_serverless and _ACTIVE_BACKEND == "sqlite"

    peak_h = max(range(24), key=lambda i: hourly_distribution[i]) if any(hourly_distribution) else 14
    peak_str = f"{peak_h:02d}:00 UTC"
    comp_rate = round((completed_learners / total_users * 100), 1) if total_users > 0 else 0

    summary_dict = {
        "total_users": total_users,
        "total_registered_users": total_users,
        "active_learners": active_learners,
        "completed_learners": completed_learners,
        "completed_graduates": completed_learners,
        "assessment_completed": assessment_completed,
        "assessment_submissions": assessment_completed,
        "total_interactions": total_interactions,
        "completion_rate": comp_rate,
        "completion_rate_percent": comp_rate,
        "peak_hour_utc": peak_str,
    }

    status_distribution_formatted = {
        "labels": ["Graduated", "Lesson", "Quiz", "AI Tutor", "Assessment", "Idle"],
        "counts": [
            status_distribution["completed"],
            status_distribution["lesson"],
            status_distribution["quiz"],
            status_distribution["tutor"],
            status_distribution["assessment"],
            status_distribution["idle"],
        ],
    }

    when_are_they_learning = {
        "time_of_day_labels": list(time_of_day_slots.keys()),
        "time_of_day_counts": list(time_of_day_slots.values()),
        "hourly_labels": [f"{h:02d}:00" for h in range(24)],
        "hourly_counts": hourly_distribution,
    }

    progression_funnel = {
        "total_modules": total_mods,
        "labels": [f"Mod {i+1}" for i in range(total_mods)],
        "lesson_counts": lesson_funnel,
    }

    return {
        "summary": summary_dict,
        "backend": _ACTIVE_BACKEND,
        "is_ephemeral": is_ephemeral,
        "database_path": _ACTIVE_SQLITE_PATH,
        "status_distribution": status_distribution_formatted,
        "status_distribution_raw": status_distribution,
        "when_are_they_learning": when_are_they_learning,
        "progression_funnel": progression_funnel,
        "hourly_distribution": hourly_distribution,
        "daily_distribution": daily_distribution,
        "time_of_day_slots": time_of_day_slots,
        "lesson_funnel": lesson_funnel,
        "survey_insights": survey_stats,
        "assessment_insights": survey_stats,
        "users": users_list,
        "recent_activity": all_logs[:30],
    }
