"""
content/curriculum.py

Static declaration of all course content. No API calls, no state, no logic
beyond pure lookup helpers.

Data model
----------
UNITS is a dict of unit_id -> unit. Each unit is an ordered list of lessons.
Each lesson maps to exactly one quiz, so the progression is always:

    lesson_1 -> quiz_1 -> lesson_2 -> quiz_2 -> ... -> unit complete

A lesson:
    id          unique within the unit
    title       short label shown in messages
    body        list of strings; each string is delivered as one WhatsApp text
                message so the bot can "stream" long lessons
    media       optional dict with keys: type ("video"|"audio"|"document"|"image"),
                url, caption, filename (only for "document")
    quiz        question, options {"A","B","C"}, correct answer letter,
                explanation shown after wrong answers

To add more content later, just append a new unit (or lesson) to UNITS.
"""

DEFAULT_UNIT_ID = "unit_1"

UNITS = {
    "unit_1": {
        "id": "unit_1",
        "title": "Unit 1: Digital Literacy for Teachers",
        "summary": "What digital literacy is, how to find and evaluate digital "
                   "resources, and how to use devices effectively in the classroom.",
        "lessons": [
            {
                "id": "lesson_1",
                "title": "Lesson 1 - What Is Digital Literacy?",
                "body": [
                    "Welcome to Unit 1! In this lesson we look at what digital literacy really means for a teacher.",
                    "Digital literacy is more than knowing how to switch on a device. It is the confident and critical use of technology to find, evaluate, create, and communicate information.",
                    "For teachers, this means three practical skills: locating good resources, judging whether they are accurate and appropriate for your students, and using them safely and effectively in your lessons.",
                    "You do not need to be a technical expert. Digital literacy is built step by step, starting with the routines you already use in your classroom."
                ],
                "media": {
                    "type": "video",
                    "url": "https://example.com/videos/digital-literacy-intro.mp4",
                    "caption": "2-minute intro video: What is digital literacy?"
                },
                "quiz": {
                    "question": "Which statement best describes digital literacy?",
                    "options": {
                        "A": "Knowing how to use a smartphone",
                        "B": "Using technology to find, evaluate, create and communicate information",
                        "C": "Replacing all paper-based teaching with computers"
                    },
                    "correct": "B",
                    "explanation": "Digital literacy covers the full process - finding, evaluating, creating and communicating - not just one device or task."
                }
            },
            {
                "id": "lesson_2",
                "title": "Lesson 2 - Finding and Evaluating Digital Resources",
                "body": [
                    "The internet is full of teaching materials, but not everything you find is accurate, relevant, or appropriate.",
                    "A simple routine when you find a new resource is to ask three questions: Is it accurate? Is it up to date? Is it suitable for my students' level, language, and context?",
                    "Free libraries such as open educational resource (OER) collections are a safer starting point because they are checked and free to reuse.",
                    "Plan for the classroom reality: always download or save resources before your lesson, because school or mobile internet can be unreliable."
                ],
                "media": {
                    "type": "document",
                    "url": "https://example.com/documents/resource-checker.pdf",
                    "filename": "resource-checker.pdf",
                    "caption": "Printable checklist: 3 questions for evaluating any resource"
                },
                "quiz": {
                    "question": "When evaluating a resource you found online, the most important question is:",
                    "options": {
                        "A": "Does it have many downloads?",
                        "B": "Is it in English?",
                        "C": "Is it accurate, up-to-date and suitable for my students?"
                    },
                    "correct": "C",
                    "explanation": "Relevance and accuracy matter most. Popularity or language alone does not make a resource good for your class."
                }
            },
            {
                "id": "lesson_3",
                "title": "Lesson 3 - Using Devices in the Classroom",
                "body": [
                    "You do not need a device for every student to teach effectively with technology.",
                    "With one projector or one phone, you can still run strong lessons: show a short video with guided questions, display an image to discuss, or use audio for listening practice.",
                    "For large classes, plan around shared moments: play, pause, and ask. Whole-class media breaks keep everyone engaged and give you time to check understanding.",
                    "Set simple rules before using any device so the technology supports learning instead of distracting from it."
                ],
                "media": {
                    "type": "image",
                    "url": "https://example.com/images/classroom-setup.png",
                    "caption": "Example: one-projector classroom seating plan"
                },
                "quiz": {
                    "question": "In a large class with only one projector, a good practice is:",
                    "options": {
                        "A": "Use whole-class media breaks combined with guided questions",
                        "B": "Wait until every student has a device",
                        "C": "Play a full video without stopping and do no activities"
                    },
                    "correct": "A",
                    "explanation": "One shared screen works when you pause, question, and discuss together - it keeps the whole class engaged."
                }
            }
        ],
        "complete_message": "Congratulations - you finished Unit 1: Digital Literacy for Teachers! Reply 'menu' to pick another unit, or type any question to ask the AI Tutor."
    }
}


def get_unit(unit_id: str):
    """Return the unit dict or None when it does not exist."""
    return UNITS.get(unit_id)


def list_lessons(unit_id: str):
    """Return the ordered list of lesson ids for a unit ([] when unknown)."""
    unit = get_unit(unit_id)
    if not unit:
        return []
    return [lesson["id"] for lesson in unit["lessons"]]


def get_lesson(unit_id: str, lesson_id: str):
    """Return the lesson dict or None."""
    unit = get_unit(unit_id)
    if not unit:
        return None
    for lesson in unit["lessons"]:
        if lesson["id"] == lesson_id:
            return lesson
    return None


def get_quiz(unit_id: str, lesson_id: str):
    """Return the quiz dict attached to a lesson or None."""
    lesson = get_lesson(unit_id, lesson_id)
    if not lesson:
        return None
    return lesson.get("quiz")


def is_valid_option(unit_id: str, lesson_id: str, option: str) -> bool:
    """Return True when option ('A','B','C'...) is a real choice for the lesson quiz."""
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return False
    return option in quiz.get("options", {})


def check_answer(unit_id: str, lesson_id: str, selected: str) -> dict:
    """
    Validate an answer for a lesson quiz.

    Returns:
        {"correct": bool, "correct_answer": str, "explanation": str}
    Raises ValueError when the lesson or quiz does not exist.
    """
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        raise ValueError(f"No quiz found for unit={unit_id!r} lesson={lesson_id!r}")
    correct_answer = quiz["correct"]
    is_correct = selected == correct_answer
    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": quiz.get("explanation", ""),
    }