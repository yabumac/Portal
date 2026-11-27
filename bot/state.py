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
    "step_index": 0,
    "quiz_question_idx": 0,
    "awaiting_response": None,
    "completed_lessons": [],
    "quiz_answers": {},
    "tutor_resume": None,
    "tutor_lesson": None,
    "tutor_history": [],
    "reflection_answers": {},
    "assessment_index": None,
    "assessment_answers": {},
    "assessment_return_to": None,
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

def is_course_complete(state: dict) -> bool:
    """Check if the user has completed all modules in their active or default course unit."""
    if not state:
        return False
    if state.get("phase") == "complete":
        return True
    unit_id = state.get("unit_id") or curriculum.DEFAULT_UNIT_ID
    lesson_ids = curriculum.list_lessons(unit_id)
    if not lesson_ids:
        return False
    lesson_idx = state.get("lesson_index")
    completed = state.get("completed_lessons") or []
    if (lesson_idx is not None and lesson_idx >= len(lesson_ids)) or len(completed) >= len(lesson_ids):
        return True
    return False


def start_unit(wa_id: str, unit_id: str = None, restart: bool = False) -> dict:
    """
    Start or resume a unit for user.
    If restart is False and user already has progress in this unit, preserves their progress!
    If the user has completed the course, preserves the completion status without looping.
    """
    unit_id = unit_id or curriculum.DEFAULT_UNIT_ID
    state = get_state(wa_id)
    lesson_ids = curriculum.list_lessons(unit_id)

    # If user already completed the course and is not explicitly restarting:
    if not restart and is_course_complete(state):
        state["phase"] = "complete"
        set_state(wa_id, state)
        return state

    # If user already has progress in this unit and not explicitly restarting, preserve exact step/quiz/awaiting state!
    has_existing = (
        not restart
        and state.get("unit_id") == unit_id
        and (
            state.get("phase") in ("lesson", "quiz", "tutor")
            or (state.get("lesson_index") or 0) > 0
            or (state.get("step_index") or 0) > 0
            or bool(state.get("quiz_answers"))
        )
    )
    if has_existing:
        curr_idx = state.get("lesson_index") or 0
        if curr_idx < len(lesson_ids):
            if state.get("phase") == "tutor":
                resumed_phase = state.get("tutor_resume") or "lesson"
                state["phase"] = resumed_phase if resumed_phase in ("lesson", "quiz") else "lesson"
                state["tutor_resume"] = None
                state["tutor_lesson"] = None
            elif state.get("phase") != "quiz":
                state["phase"] = "lesson"
            set_state(wa_id, state)
            db.log_activity(wa_id, "course_resumed", f"Resumed {unit_id} at Module {curr_idx + 1}, Step {state.get('step_index', 0)}")
            return state
        else:
            state["phase"] = "complete"
            set_state(wa_id, state)
            return state

    state.update({
        "phase": "lesson",
        "unit_id": unit_id,
        "lesson_index": 0 if restart or state.get("lesson_index") is None else state.get("lesson_index", 0),
        "step_index": 0 if restart else state.get("step_index", 0),
        "quiz_question_idx": 0,
        "awaiting_response": None,
        "tutor_resume": None,
        "tutor_lesson": None,
        "tutor_history": [],
        "assessment_index": None,
    })
    if restart:
        state["completed_lessons"] = []
        state["quiz_answers"] = {}
        state["lesson_index"] = 0
        state["step_index"] = 0
        state["quiz_question_idx"] = 0

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


def record_quiz_result(wa_id: str, lesson_id: str, answer: str, correct: bool, question_idx: int = 0) -> None:
    """Record user's quiz submission in state and database activity log."""
    state = get_state(wa_id)
    quizzes = state.get("quiz_answers") or {}
    key = f"{lesson_id}_q{question_idx + 1}" if question_idx > 0 else lesson_id
    quizzes[key] = {
        "answer": answer,
        "correct": correct,
        "question_idx": question_idx,
    }
    state["quiz_answers"] = quizzes
    set_state(wa_id, state)
    status_label = "Correct" if correct else "Incorrect"
    db.log_activity(wa_id, "quiz_answered", f"{lesson_id} (Q{question_idx + 1}): Option {answer} ({status_label})")


def advance_past_lesson(wa_id: str):
    """
    Called after passing all quiz questions for a lesson. Marks current lesson as completed and advances.
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
        state.update({
            "lesson_index": next_index,
            "step_index": 0,
            "quiz_question_idx": 0,
            "awaiting_response": None,
            "phase": "lesson"
        })
        set_state(wa_id, state)
        next_les = curriculum.get_lesson(unit_id, lesson_ids[next_index])
        db.log_activity(wa_id, "lesson_advanced", f"Advanced to {next_les['title']} ({next_index+1}/{len(lesson_ids)})")
        return "lesson", next_les

    # Course completed!
    state.update({
        "phase": "complete",
        "lesson_index": len(lesson_ids),
        "step_index": 0,
        "quiz_question_idx": 0,
        "awaiting_response": None
    })
    set_state(wa_id, state)
    db.log_activity(wa_id, "course_completed", f"Completed all {len(lesson_ids)} modules in {unit_id}!")
    return "complete", None


# --- Tutor mode --------------------------------------------------------------

def enter_tutor(wa_id: str, lesson_id: str = None) -> dict:
    state = get_state(wa_id)
    curr_phase = state.get("phase", "idle")
    # Preserve existing resume target if user is already in tutor mode
    if is_course_complete(state) or curr_phase == "complete":
        resume = "complete"
    elif curr_phase == "tutor":
        resume = state.get("tutor_resume") or "idle"
        lesson_id = lesson_id or state.get("tutor_lesson")
    elif curr_phase in ("lesson", "quiz"):
        resume = curr_phase
    else:
        resume = "idle"

    if curr_phase != "tutor":
        state["tutor_history"] = []

    state.update({
        "phase": "tutor",
        "tutor_resume": resume,
        "tutor_lesson": lesson_id,
    })
    set_state(wa_id, state)
    db.log_activity(wa_id, "tutor_entered", f"Context: {lesson_id or 'General'}")
    return state


def append_tutor_turn(wa_id: str, question: str, answer: str, max_turns: int = 8) -> None:
    """Append a user/model exchange to the active AI chat history."""
    state = get_state(wa_id)
    history = list(state.get("tutor_history") or [])
    history.append({"role": "user", "text": question[:1000]})
    history.append({"role": "model", "text": answer[:1500]})
    # Keep at most max_turns pairs (2 messages per turn)
    if len(history) > max_turns * 2:
        history = history[-(max_turns * 2):]
    state["tutor_history"] = history
    set_state(wa_id, state)


def exit_tutor(wa_id: str) -> str:
    state = get_state(wa_id)
    resume = state.get("tutor_resume") or "idle"
    if is_course_complete(state):
        resume = "complete"
    state.update({
        "phase": resume,
        "tutor_resume": None,
        "tutor_lesson": None,
        "tutor_history": [],
    })
    set_state(wa_id, state)
    db.log_activity(wa_id, "tutor_exited", f"Returned to {resume}")
    return state["phase"]


def record_reflection_answer(wa_id: str, key: str, user_text: str, ai_feedback: str) -> None:
    """Persist teacher's typed reflection response and AI feedback for admin reporting."""
    state = get_state(wa_id)
    reflections = dict(state.get("reflection_answers") or {})
    reflections[key] = {
        "answer": user_text[:1000],
        "feedback": ai_feedback[:1500],
    }
    state["reflection_answers"] = reflections
    set_state(wa_id, state)


# --- Self-Assessment ---------------------------------------------------------

def start_assessment(wa_id: str, return_to: str = "menu") -> dict:
    state = get_state(wa_id)
    state.update({
        "phase": "assessment",
        "assessment_index": 0,
        "assessment_answers": {},
        "assessment_return_to": return_to,
        "tutor_resume": None,
        "tutor_lesson": None,
    })
    set_state(wa_id, state)
    db.log_activity(wa_id, "assessment_started", f"Started AI Self-Assessment (return_to={return_to})")
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
    return_to = state.get("assessment_return_to") or "menu"
    state.update({
        "assessment_answers": answers,
        "assessment_index": next_index,
    })
    if done:
        state["assessment_return_to"] = None
        if return_to == "step_1":
            state["phase"] = "lesson"
            state["step_index"] = 1
        elif is_course_complete(state):
            state["phase"] = "complete"
        elif (state.get("step_index") or 0) > 0:
            state["phase"] = "lesson"
        else:
            state["phase"] = "idle"
    set_state(wa_id, state)
    db.log_activity(wa_id, "assessment_answered", f"{question_id} = {letter}")
    if done:
        db.log_activity(wa_id, "assessment_completed", "Completed AI Self-Assessment")
    return {"done": done, "answers": answers, "return_to": return_to}


def abort_assessment(wa_id: str) -> None:
    state = get_state(wa_id)
    if is_course_complete(state):
        next_phase = "complete"
    elif state.get("assessment_return_to") == "step_1" or (state.get("step_index") or 0) > 0:
        next_phase = "lesson"
    else:
        next_phase = "idle"
    state.update({
        "phase": next_phase,
        "assessment_index": None,
        "assessment_return_to": None,
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
