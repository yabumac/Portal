"""
bot/state.py

User state + course progression + mode tracking.

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

State shape
-----------
    {
        "phase":           "idle" | "lesson" | "quiz" | "tutor" | "assessment" | "complete",
        "unit_id":         str | None,
        "lesson_index":    int | None,        # index into curriculum.list_lessons(unit_id)
        "tutor_resume":    str | None,        # phase before entering tutor ("lesson"/"quiz"/"idle")
        "tutor_lesson":    str | None,        # lesson id context for the tutor
        "assessment_index":    int | None,    # next question index
        "assessment_answers":  dict | None,   # {question_id: "A"/"B"/"C"}
    }

Phases:
    idle        no course active; free text goes to the AI Tutor (full course context)
    lesson      lesson just delivered; user sees Ask AI / Continue buttons
    quiz        quiz on screen; awaiting answer button (A/B/C)
    tutor       AI tutor mode active; free text goes to AI with parsed context
    assessment  self-assessment mini-form running
    complete    unit finished; user can restart or enter tutor
"""

import copy
import logging

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

# --- Storage layer -----------------------------------------------------------
USER_STATE: dict = {}

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
    return copy.deepcopy(state) if state else copy.deepcopy(IDLE_STATE)


def set_state(wa_id: str, state: dict) -> None:
    USER_STATE[wa_id] = state


def del_state(wa_id: str) -> None:
    USER_STATE.pop(wa_id, None)


# --- Course progression ------------------------------------------------------

def start_unit(wa_id: str, unit_id: str) -> dict:
    """Reset a user into the first lesson of a unit."""
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
    """Return the lesson dict the user is currently on, or None."""
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
    """
    Called after a correct quiz answer. Advances to the next lesson or
    finishes the unit.

    Returns:
        ("lesson", lesson_dict) when more lessons remain.
        ("complete", None) when the unit is finished.
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


# --- Tutor mode --------------------------------------------------------------

def enter_tutor(wa_id: str, lesson_id: str = None) -> dict:
    """
    Enter tutor mode. Saves the phase we should return to when exiting.
    If lesson_id is provided the tutor gets that lesson's context.
    """
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
    """
    Exit tutor mode and return the phase to restore ("lesson", "quiz", or
    "idle").
    """
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
    """
    Record a single assessment answer.

    Returns:
        {"done": bool, "answers": dict}
    """
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
    """Exit the assessment back to idle."""
    state = get_state(wa_id)
    state.update({
        "phase": "idle",
        "assessment_index": None,
        "assessment_answers": None,
    })
    set_state(wa_id, state)


# --- Reset -------------------------------------------------------------------

def reset(wa_id: str) -> None:
    """Delete all progress for a user."""
    del_state(wa_id)