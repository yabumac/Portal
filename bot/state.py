"""
bot/state.py

User state + course progression + mode tracking with persistent database storage.
Keyed by actual phone number (wa_id) received from WhatsApp.
"""

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

from bot import db
from content import curriculum

logger = logging.getLogger("whatsapp_bot")

IDLE_STATE = {
    "phase": "idle",
    "unit_id": curriculum.DEFAULT_UNIT_ID,
    "lesson_index": 0,
    "completed_lessons": [],
    "quiz_answers": {},
    "tutor_resume": None,
    "tutor_lesson": None,
    "assessment_index": None,
    "assessment_answers": {},
    "total_messages": 0,
}


def get_state(wa_id: str) -> dict:
    """Retrieve user state from database by phone number."""
    phone = str(wa_id).strip()
    stored = db.get_user_state(phone)
    if stored is None:
        fresh = copy.deepcopy(IDLE_STATE)
        fresh["phone_number"] = phone
        # Note: Do not overwrite if user just pinged; save default
        db.save_user_state(phone, fresh)
        return fresh

    # Ensure defaults for backward compatibility
    for k, v in IDLE_STATE.items():
        if k not in stored:
            stored[k] = copy.deepcopy(v)
    return stored


def set_state(wa_id: str, state: dict) -> None:
    """Save user state to persistent database."""
    phone = str(wa_id).strip()
    db.save_user_state(phone, state)


def del_state(wa_id: str) -> None:
    """Delete a user's state from the database."""
    phone = str(wa_id).strip()
    db.delete_user(phone)


# --- Course progression ------------------------------------------------------

def start_unit(wa_id: str, unit_id: str = None, restart: bool = False) -> dict:
    """
    Start or resume a unit for user.
    If restart is False and user already has progress in this unit, preserves their progress!
    """
    unit_id = unit_id or curriculum.DEFAULT_UNIT_ID
    state = get_state(wa_id)

    # If user already has progress and not explicitly restarting, don't wipe!
    if not restart and state.get("unit_id") == unit_id and state.get("lesson_index") is not None and state.get("lesson_index", 0) > 0:
        state["phase"] = "lesson"
        set_state(wa_id, state)
        db.log_activity(wa_id, "course_resumed", f"Resumed {unit_id} at Lesson {(state.get('lesson_index', 0) + 1)}")
        return state

    state.update({
        "phase": "lesson",
        "unit_id": unit_id,
        "lesson_index": 0 if restart or state.get("lesson_index") is None else state.get("lesson_index", 0),
        "tutor_resume": None,
        "tutor_lesson": None,
        "assessment_index": None,
    })
    if restart:
        state["completed_lessons"] = []
        state["quiz_answers"] = {}
        state["lesson_index"] = 0

    set_state(wa_id, state)
    event_name = "course_restarted" if restart else "course_enrolled"
    db.log_activity(wa_id, event_name, f"Enrolled in {unit_id}")
    return state


def current_lesson(state: dict):
    """
    Resolve the active lesson object for the user.
    Resilient: falls back to safe bounds instead of failing with None.
    """
    unit_id = state.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson_index = state.get("lesson_index")
    if lesson_index is None:
        lesson_index = 0

    lesson_ids = curriculum.list_lessons(unit_id)
    if not lesson_ids:
        return None

    if lesson_index >= len(lesson_ids):
        # Already finished all lessons
        return None

    idx = max(0, min(lesson_index, len(lesson_ids) - 1))
    return curriculum.get_lesson(unit_id, lesson_ids[idx])


def open_quiz(wa_id: str) -> dict:
    """Switch user phase to quiz."""
    state = get_state(wa_id)
    state["phase"] = "quiz"
    set_state(wa_id, state)
    lesson = current_lesson(state)
    lesson_title = lesson["title"] if lesson else f"Lesson {state.get('lesson_index', 0)+1}"
    db.log_activity(wa_id, "quiz_opened", f"Opened quiz for {lesson_title}")
    return state


def record_quiz_result(wa_id: str, lesson_id: str, answer: str, correct: bool) -> None:
    """Record user's quiz submission in state and database activity log."""
    state = get_state(wa_id)
    quizzes = state.get("quiz_answers") or {}
    quizzes[lesson_id] = {
        "answer": answer,
        "correct": correct,
    }
    state["quiz_answers"] = quizzes
    set_state(wa_id, state)
    status_label = "Correct" if correct else "Incorrect"
    db.log_activity(wa_id, "quiz_answered", f"{lesson_id}: Option {answer} ({status_label})")


def advance_past_lesson(wa_id: str):
    """
    Called after passing a quiz. Marks current lesson as completed and advances.
    """
    state = get_state(wa_id)
    unit_id = state.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson_ids = curriculum.list_lessons(unit_id)
    current_idx = state.get("lesson_index", 0)

    # Mark current lesson completed
    completed = state.get("completed_lessons") or []
    if current_idx < len(lesson_ids):
        curr_id = lesson_ids[current_idx]
        if curr_id not in completed:
            completed.append(curr_id)
    state["completed_lessons"] = completed

    next_index = current_idx + 1

    if next_index < len(lesson_ids):
        state.update({"lesson_index": next_index, "phase": "lesson"})
        set_state(wa_id, state)
        next_les = curriculum.get_lesson(unit_id, lesson_ids[next_index])
        db.log_activity(wa_id, "lesson_advanced", f"Advanced to {next_les['title']} ({next_index+1}/{len(lesson_ids)})")
        return "lesson", next_les

    # Course completed!
    state.update({"phase": "complete", "lesson_index": len(lesson_ids)})
    set_state(wa_id, state)
    db.log_activity(wa_id, "course_completed", f"Completed all {len(lesson_ids)} modules in {unit_id}!")
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
    db.log_activity(wa_id, "tutor_entered", f"Context: {lesson_id or 'General'}")
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
    db.log_activity(wa_id, "tutor_exited", f"Returned to {resume}")
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
    db.log_activity(wa_id, "assessment_started", "Started AI Self-Assessment")
    return state


def assessment_index(wa_id: str) -> int:
    state = get_state(wa_id)
    idx = state.get("assessment_index")
    return idx if idx is not None else 0


def record_assessment_answer(wa_id: str, question_id: str, letter: str) -> dict:
    state = get_state(wa_id)
    answers = state.get("assessment_answers") or {}
    answers[question_id] = letter
    curr_index = state.get("assessment_index")
    if curr_index is None:
        curr_index = 0
    next_index = curr_index + 1
    done = next_index >= len(curriculum.ASSESSMENT)
    state.update({
        "assessment_answers": answers,
        "assessment_index": next_index,
    })
    if done:
        state["phase"] = "idle"
    set_state(wa_id, state)
    db.log_activity(wa_id, "assessment_answered", f"{question_id} = {letter}")
    if done:
        db.log_activity(wa_id, "assessment_completed", "Completed AI Self-Assessment")
    return {"done": done, "answers": answers}


def abort_assessment(wa_id: str) -> None:
    state = get_state(wa_id)
    state.update({
        "phase": "idle",
        "assessment_index": None,
        "assessment_answers": None,
    })
    set_state(wa_id, state)
    db.log_activity(wa_id, "assessment_aborted", "Exited AI Self-Assessment")


# --- Reset / Admin helpers ---------------------------------------------------

def reset(wa_id: str) -> None:
    """Reset user state to fresh idle state."""
    fresh = copy.deepcopy(IDLE_STATE)
    fresh["phone_number"] = wa_id
    set_state(wa_id, fresh)
    db.log_activity(wa_id, "user_reset", "User state reset by admin/system")


def get_all_users() -> dict:
    return db.get_all_users()
