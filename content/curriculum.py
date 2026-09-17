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

Other content:
    INTRO_VIDEO_URL  public link to the logo / intro video (drop your file in
                     /media and host it somewhere public, then paste the link)
    BOT_INTRO        the welcome text shown on the first message
    ASSESSMENT       the AI Self-Assessment mini-form (A/B/C per question)
"""

# ---------------------------------------------------------------------------
# Intro assets
# ---------------------------------------------------------------------------
# PUT YOUR LOGO VIDEO LINK HERE. Drop the video file into /media/INTRO_VIDEO.mp4
# then publish it somewhere public (Vercel Blob, Cloudinary, any direct .mp4
# link) and paste the link below. WhatsApp needs a public URL to send media.
INTRO_VIDEO_URL = "https://YOUR-PUBLIC-LINK-HERE/edtech-hub-intro.mp4"

BOT_INTRO = (
    "Welcome to EdTech Hub! This bot is your AI learning companion for "
    "educators.\n\n"
    "You get two things here:\n"
    "1. AI Guidance - ask me any teaching question and I will answer using "
    "your course material.\n"
    "2. AI for Educators - a step-by-step micro-course with lessons, videos, "
    "documents and quizzes.\n\n"
    "Choose an option below to get started."
)

# ---------------------------------------------------------------------------
# AI Self-Assessment (short data-collection form)
# ---------------------------------------------------------------------------
ASSESSMENT = [
    {
        "id": "ai_use",
        "question": "How often do you currently use AI tools in your teaching?",
        "options": {
            "A": "Never tried them yet",
            "B": "Sometimes",
            "C": "Regularly",
        },
    },
    {
        "id": "comfort",
        "question": "How confident do you feel about using AI tools?",
        "options": {
            "A": "Not confident yet",
            "B": "Somewhat confident",
            "C": "Very confident",
        },
    },
    {
        "id": "challenge",
        "question": "What is your biggest challenge with AI right now?",
        "options": {
            "A": "I don't know where to start",
            "B": "Limited access to devices or internet",
            "C": "Worried about students misusing it",
        },
    },
    {
        "id": "goal",
        "question": "What do you most want from this course?",
        "options": {
            "A": "Practical lesson ideas",
            "B": "Time-saving tools",
            "C": "Using AI responsibly and safely",
        },
    },
]

# ---------------------------------------------------------------------------
# Course content
# ---------------------------------------------------------------------------
DEFAULT_UNIT_ID = "unit_1"

UNITS = {
    "unit_1": {
        "id": "unit_1",
        "title": "Unit 1: AI for Educators - The Basics",
        "summary": "What AI means for teachers, how to use and evaluate AI tools, "
                   "and how to teach with AI responsibly in your classroom.",
        "lessons": [
            {
                "id": "lesson_1",
                "title": "Lesson 1 - What Is AI in Education?",
                "body": [
                    "Welcome to the AI for Educators course! In this first lesson we look at what AI actually means for you and your classroom.",
                    "AI refers to computer systems that can do tasks that normally need human intelligence - like understanding language, answering questions, generating ideas, or giving feedback on student work.",
                    "In education, AI shows up in everyday ways: lesson-planning assistants, tutoring chatbots, automatic quizzes, translation tools, and tools that help you draft feedback on assignments.",
                    "AI is a helper, not a replacement. The teacher still decides what to teach, how to teach it, and what is right for each student."
                ],
                "media": {
                    "type": "video",
                    "url": "https://example.com/videos/ai-in-education-intro.mp4",
                    "caption": "2-minute intro video: What is AI in education?"
                },
                "quiz": {
                    "question": "Which best describes how AI can help a teacher?",
                    "options": {
                        "A": "It replaces the teacher in the classroom",
                        "B": "It handles repetitive tasks like drafting ideas, quizzes and feedback so the teacher can focus on students",
                        "C": "It automatically removes anything the students find difficult"
                    },
                    "correct": "B",
                    "explanation": "AI saves time on repetitive work, but the teacher always stays in charge of teaching decisions."
                }
            },
            {
                "id": "lesson_2",
                "title": "Lesson 2 - Using and Evaluating AI Tools",
                "body": [
                    "The quality of an AI answer depends on the quality of your request. Be specific: state the topic, the student level, how many examples, and the format you want.",
                    "Always review AI output before you use it. Check for accuracy, bias, and whether it matches your curriculum and your students.",
                    "Build a reliable habit: generate, check, adapt, and only then use. Treat AI output as a first draft, never as the final word."
                ],
                "media": {
                    "type": "document",
                    "url": "https://example.com/documents/ai-prompt-guide.pdf",
                    "filename": "ai-prompt-guide.pdf",
                    "caption": "Printable guide: how to prompt AI tools for lesson ideas"
                },
                "quiz": {
                    "question": "When using an AI tool for your teaching, the most important habit is:",
                    "options": {
                        "A": "Use the first result it gives without reading it",
                        "B": "Review, check, and adapt the output before using it",
                        "C": "Ask the tool to make its answers longer"
                    },
                    "correct": "B",
                    "explanation": "AI is a first draft. You are the expert - always review, check and adapt before using it."
                }
            },
            {
                "id": "lesson_3",
                "title": "Lesson 3 - Teaching AI Responsibly",
                "body": [
                    "Set clear rules on when and how your students may use AI tools, and teach them to credit AI sources just like any other source.",
                    "Protect privacy: never enter students' personal data into tools you have not checked. Keep the data to a minimum and follow your school's policies.",
                    "AI can widen the gap between students with and without access. Plan low-tech alternatives so every learner can take part."
                ],
                "media": {
                    "type": "image",
                    "url": "https://example.com/images/responsible-ai-poster.png",
                    "caption": "Poster: responsible AI use in the classroom"
                },
                "quiz": {
                    "question": "Before you enter information about a student into an AI tool, you should:",
                    "options": {
                        "A": "Check the tool's privacy policy and keep personal data to a minimum",
                        "B": "Share complete student records so the tool gives better answers",
                        "C": "Ask the student to type the data themselves"
                    },
                    "correct": "A",
                    "explanation": "Student privacy comes first. Check privacy policies and only share the minimum needed."
                }
            }
        ],
        "complete_message": "Congratulations - you completed Unit 1 of AI for Educators! Reply 'menu' to pick another option, or tap Ask AI Tutor any time for guidance."
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


def quiz_as_context(unit_id: str, lesson_id: str) -> str:
    """Plain-text block of the lesson quiz, used as the AI tutor context."""
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return ""
    options = "; ".join(f"{letter}) {text}" for letter, text in quiz["options"].items())
    return f"QUIZ QUESTION: {quiz['question']}\nOPTIONS: {options}"

def lesson_as_context(unit_id: str, lesson_id: str) -> str:
    """Plain-text block of an entire lesson, used as the AI tutor context."""
    lesson = get_lesson(unit_id, lesson_id)
    if not lesson:
        return ""
    body = " ".join(lesson["body"])
    quiz_block = quiz_as_context(unit_id, lesson_id)
    block = f"LESSON: {lesson['title']}\n{body}"
    if quiz_block:
        block += f"\n{quiz_block}"
    return block


def get_assessment_question(index: int):
    """Return the assessment question at index, or None when out of range."""
    if 0 <= index < len(ASSESSMENT):
        return ASSESSMENT[index]
    return None