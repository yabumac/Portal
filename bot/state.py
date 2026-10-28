"""
bot/state.py

User state + course progression + mode tracking with persistent storage.
"""

import copy
import json
import logging
import os

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

# --- Storage layer -----------------------------------------------------------
USER_STATE: dict = {}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp")
TMP_USERS_FILE = os.path.join(TMP_DIR, "users.json")
# Also try /tmp for serverless environments (Vercel, etc.)
SYSTEM_TMP = os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
SYSTEM_TMP_USERS_FILE = os.path.join(SYSTEM_TMP, "whatsapp_bot_users.json") if SYSTEM_TMP else None


def _ensure_data_dir():
    for d in (DATA_DIR, TMP_DIR):
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


def _load_from_path(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None


def _load_all() -> dict:
    _ensure_data_dir()
    # Try multiple locations in order of preference
    for candidate in (USERS_FILE, TMP_USERS_FILE, SYSTEM_TMP_USERS_FILE):
        if not candidate:
            continue
        data = _load_from_path(candidate)
        if not data:
            continue
        if isinstance(data.get("users"), dict):
            return data
        elif isinstance(data, dict) and data and all(isinstance(v, dict) for v in data.values()):
            return {"users": data}
    return {}


def _save_to_path(path: str, data: dict) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        logger.warning(f"Failed to save to {path}: {e}")
        return False


def _save_all(data: dict) -> None:
    _ensure_data_dir()
    saved = False
    for candidate in (USERS_FILE, TMP_USERS_FILE, SYSTEM_TMP_USERS_FILE):
        if not candidate:
            continue
        if _save_to_path(candidate, data):
            saved = True
    if not saved:
        logger.warning("Failed to persist user state to any location")


# Initialize from disk
try:
    _disk_state = _load_all()
    if isinstance(_disk_state.get("users"), dict):
        USER_STATE = _disk_state["users"]
    elif isinstance(_disk_state, dict) and _disk_state and all(isinstance(v, dict) for v in _disk_state.values()):
        USER_STATE = _disk_state
    else:
        USER_STATE = {}
except Exception:
    USER_STATE = {}


IDLE_STATE = {
    "phase": "idle",
    "unit_id": None,
    "lesson_index": None,
    "tutor_resume": None,
    "tutor_lesson": None,
    "assessment_index": None,
    "assessment_answers": None,
}


def get_state(wa_id: str) -> dict:
    state = USER_STATE.get(wa_id)
    if state is None:
        try:
            all_data = _load_all()
            users = all_data.get("users") if isinstance(all_data.get("users"), dict) else all_data
            if isinstance(users, dict) and wa_id in users:
                state = users[wa_id]
                USER_STATE[wa_id] = state
        except Exception:
            pass
    if state is None:
        return copy.deepcopy(IDLE_STATE)
    # ensure metadata
    try:
        if "created_at" not in state:
            from datetime import datetime
            state["created_at"] = datetime.utcnow().isoformat() + "Z"
        from datetime import datetime
        state["last_seen"] = datetime.utcnow().isoformat() + "Z"
        USER_STATE[wa_id] = state
    except Exception:
        pass
    return copy.deepcopy(state)


def set_state(wa_id: str, state: dict) -> None:
    try:
        from datetime import datetime
        state["last_seen"] = datetime.utcnow().isoformat() + "Z"
        if "created_at" not in state:
            state["created_at"] = state["last_seen"]
    except Exception:
        pass
    USER_STATE[wa_id] = copy.deepcopy(state)
    try:
        _save_all({"users": USER_STATE})
    except Exception as e:
        logger.warning(f"Failed to persist state for {wa_id}: {e}")


def del_state(wa_id: str) -> None:
    USER_STATE.pop(wa_id, None)
    try:
        _save_all({"users": USER_STATE})
    except Exception:
        pass


# --- Course progression ------------------------------------------------------

def start_unit(wa_id: str, unit_id: str) -> dict:
    state = get_state(wa_id)
    state.update({
        "phase": "lesson",
        "unit_id": unit_id,
        "lesson_index": 0,
        "tutor_resume": None,
        "tutor_lesson": None,
        "assessment_index": None,
        "assessment_answers": None,
    })
    set_state(wa_id, state)
    return state


def current_lesson(state: dict):
    phase = state.get("phase")
    if phase not in ("lesson", "quiz"):
        return None
    unit_id = state.get("unit_id")
    lesson_index = state.get("lesson_index")
    if not unit_id or lesson_index is None:
        return None
    lesson_ids = curriculum.list_lessons(unit_id)
    if lesson_index >= len(lesson_ids):
        return None
    return curriculum.get_lesson(unit_id, lesson_ids[lesson_index])


def open_quiz(wa_id: str) -> dict:
    state = get_state(wa_id)
    state["phase"] = "quiz"
    set_state(wa_id, state)
    return state


def advance_past_lesson(wa_id: str):
    state = get_state(wa_id)
    lesson_ids = curriculum.list_lessons(state.get("unit_id"))
    next_index = state.get("lesson_index", -1) + 1

    if next_index < len(lesson_ids):
        state.update({"lesson_index": next_index, "phase": "lesson"})
        set_state(wa_id, state)
        return "lesson", curriculum.get_lesson(state["unit_id"], lesson_ids[next_index])

    state.update({"phase": "complete", "lesson_index": None})
    set_state(wa_id, state)
    return "complete", None


# --- Tutor mode --------------------------------------------------------------

def enter_tutor(wa_id: str, lesson_id: str = None) -> dict:
    state = get_state(wa_id)
    resume = state.get("phase", "idle")
    if resume not in ("lesson", "quiz"):
        resume = "idle"
    state.update({
        "phase": "tutor",
        "tutor_resume": resume,
        "tutor_lesson": lesson_id,
    })
    set_state(wa_id, state)
    return state


def exit_tutor(wa_id: str) -> str:
    state = get_state(wa_id)
    resume = state.get("tutor_resume", "idle")
    state.update({
        "phase": resume,
        "tutor_resume": None,
        "tutor_lesson": None,
    })
    set_state(wa_id, state)
    return state["phase"]


# --- Self-Assessment ---------------------------------------------------------

def start_assessment(wa_id: str) -> dict:
    state = get_state(wa_id)
    state.update({
        "phase": "assessment",
        "assessment_index": 0,
        "assessment_answers": {},
        "tutor_resume": None,
        "tutor_lesson": None,
    })
    set_state(wa_id, state)
    return state


def assessment_index(wa_id: str) -> int:
    state = get_state(wa_id)
    return state.get("assessment_index", 0)


def record_assessment_answer(wa_id: str, question_id: str, letter: str) -> dict:
    state = get_state(wa_id)
    answers = state.get("assessment_answers") or {}
    answers[question_id] = letter
    next_index = state.get("assessment_index", 0) + 1
    done = next_index >= len(curriculum.ASSESSMENT)
    state.update({
        "assessment_answers": answers,
        "assessment_index": next_index,
    })
    if done:
        state["phase"] = "idle"
    set_state(wa_id, state)
    return {"done": done, "answers": answers}


def abort_assessment(wa_id: str) -> None:
    state = get_state(wa_id)
    state.update({
        "phase": "idle",
        "assessment_index": None,
        "assessment_answers": None,
    })
    set_state(wa_id, state)


# --- Reset / Admin helpers ---------------------------------------------------

def reset(wa_id: str) -> None:
    del_state(wa_id)


def get_all_users() -> dict:
    try:
        all_data = _load_all()
        users = all_data.get("users") if isinstance(all_data.get("users"), dict) else all_data
        if isinstance(users, dict):
            return copy.deepcopy(users)
    except Exception:
        pass
    return copy.deepcopy(USER_STATE)
