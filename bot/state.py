"""
bot/state.py

User state + course progression.

Storage layer
-------------
USER_STATE is a plain in-memory dict keyed by WhatsApp id. This works for a
single-function process (local dev). Vercel serverless functions are stateless
and can cold-start between requests, so the in-memory dict can lose progress
at any time.

Production upgrade
------------------
Swap ONLY the three storage functions (get_state / set_state / del_state) with
a real database - for example Upstash Redis or Supabase. Keep the same
signatures and every caller above the storage layer works unchanged.

    # example: Redis (Upstash)
    import os, json, redis
    _r = redis.from_url(os.getenv("UPSTASH_REDIS_REST_URL"))
    def get_state(wa_id):
        raw = _r.get(f"user:{wa_id}")
        return json.loads(raw) if raw else IDLE_STATE.copy()
    def set_state(wa_id, state):
        _r.set(f"user:{wa_id}", json.dumps(state))
    def del_state(wa_id):
        _r.delete(f"user:{wa_id}")

State shape
-----------
    {
        "phase": "idle" | "lesson" | "quiz" | "complete",
        "unit_id": str | None,       # e.g. "unit_1"
        "lesson_index": int | None,  # index into curriculum.list_lessons(unit_id)
    }

Phases:
    idle      no course running; free text goes to the AI Tutor
    lesson    lesson text just delivered; awaiting "Ready for Quiz?"
    quiz      quiz question on screen; awaiting answer button (A/B/C)
    complete  unit finished; user can restart or ask the AI Tutor
"""

import copy
import logging

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

# --- Storage layer: swap for Redis/Supabase in production (see docstring) ---
USER_STATE: dict = {}

IDLE_STATE = {"phase": "idle", "unit_id": None, "lesson_index": None}


def get_state(wa_id: str) -> dict:
    """Return a copy of the user's state (never a live reference)."""
    state = USER_STATE.get(wa_id)
    return copy.deepcopy(state) if state else copy.deepcopy(IDLE_STATE)


def set_state(wa_id: str, state: dict) -> None:
    USER_STATE[wa_id] = state


def del_state(wa_id: str) -> None:
    USER_STATE.pop(wa_id, None)


# --- Progression helpers -----------------------------------------------------

def start_unit(wa_id: str, unit_id: str) -> dict:
    """Reset a user into the first lesson of a unit."""
    state = get_state(wa_id)
    state.update({"phase": "lesson", "unit_id": unit_id, "lesson_index": 0})
    set_state(wa_id, state)
    return state


def current_lesson(state: dict):
    """
    Return the lesson dict the user is currently on, or None.
    Only valid while a course is active (phase lesson/quiz).
    """
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
    """Move the user into the quiz phase (awaits an A/B/C answer)."""
    state = get_state(wa_id)
    state["phase"] = "quiz"
    set_state(wa_id, state)
    return state


def advance_past_lesson(wa_id: str):
    """
    Called after a correct quiz answer. Advances to the next lesson or
    finishes the unit.

    Returns:
        ("lesson", lesson_dict) when more lessons remain.
        ("complete", None) when the unit is finished (phase -> "complete").
    """
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


def reset(wa_id: str) -> None:
    """Delete all progress for a user."""
    del_state(wa_id)