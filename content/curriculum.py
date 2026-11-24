"""
content/curriculum.py

Curriculum data for "AI for Teaching and Learning (Ethiopian Educators Edition)".
Visual- and video-first learning structure with concise, professional instruction.
Zero childish emojis, clean pedagogy, and direct video clip integration.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

DEFAULT_UNIT_ID = "unit_1"
COURSE_TITLE = "Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia"

# Intro Media Assets
INTRO_VIDEO_FILENAME = "vid_01_welcome.mp4"
INTRO_LOGO_FILENAME = "logo.png"

COURSE_DESCRIPTION = (
    "This introductory course equips Ethiopian primary and secondary school teachers with basic knowledge "
    "and practical skills to understand and use Artificial Intelligence (AI) in teaching and learning. "
    "Teachers will explore accessible AI tools and learn how to use them for lesson preparation, developing "
    "learning materials, creating assessments, and supporting student learning. The course also introduces "
    "responsible and ethical AI use in education."
)

LEARNING_OBJECTIVES = (
    "By the end of the course, teachers will be able to:\n"
    "• Explain AI and its applications in education.\n"
    "• Identify and use basic AI tools such as ChatGPT, Gemini and Copilot.\n"
    "• Write simple prompts to obtain useful AI-generated responses.\n"
    "• Use AI to prepare lesson plans, teaching materials and assessment questions.\n"
    "• Apply basic ethical principles when using AI in education."
)

BOT_INTRO = (
    "Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia\n\n"
    "Course description\n"
    f"{COURSE_DESCRIPTION}\n\n"
    "Learning objectives\n"
    f"{LEARNING_OBJECTIVES}\n\n"
    "Tap Continue below to begin Section 1, or Ask AI Tutor if you have any questions:"
)

MODULE_1_CLOSING = (
    "Module 1: Closing\n\n"
    "Congratulations! You have completed the course on understanding Artificial Intelligence.\n\n"
    "You have learned what AI is, how it works, examples of AI in everyday life, and how it can support teaching and learning.\n\n"
    "Remember, AI is a tool to support your work, not replace your knowledge, creativity and professional judgment as a teacher.\n\n"
    "You have finished the entire course! You can return to the Main Menu, ask the AI Tutor questions, or review and restart the module below."
)

# ---------------------------------------------------------------------------
# Teacher AI Readiness & Needs Survey
# ---------------------------------------------------------------------------
ASSESSMENT = [
    {
        "id": "ai_use",
        "question": "How often do you currently use AI tools in your teaching practice?",
        "options": {
            "A": "I have not used them yet",
            "B": "Occasionally for lesson preparation and ideas",
            "C": "Regularly in my weekly workflow",
        },
    },
    {
        "id": "comfort",
        "question": "How confident do you feel applying AI tools in your classroom?",
        "options": {
            "A": "Not confident yet",
            "B": "Somewhat confident",
            "C": "Very confident",
        },
    },
    {
        "id": "challenge",
        "question": "What is your primary constraint regarding technology in school?",
        "options": {
            "A": "Large class sizes (50+ students)",
            "B": "Limited devices or intermittent electricity/internet",
            "C": "Formulating clear, effective prompts",
        },
    },
    {
        "id": "goal",
        "question": "What is your main goal for completing this course?",
        "options": {
            "A": "Practical teaching activities tailored to Ethiopian schools",
            "B": "Time-saving planning and assessment strategies",
            "C": "Ethical, responsible, and privacy-first classroom use",
        },
    },
]

# ---------------------------------------------------------------------------
# Course Content: 7 Modules with Video Clips and Visual Diagrams
# ---------------------------------------------------------------------------
UNITS = {
    "unit_1": {
        "id": "unit_1",
        "title": "AI for Teaching and Learning (Ethiopian Educators Edition)",
        "summary": (
            "A practical guide for educators in Ethiopia to leverage AI for lesson planning, "
            "formative assessment, Universal Design for Learning, and ethical pedagogy."
        ),
        "complete_message": (
            "Congratulations on completing Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia!\n\n"
            "You have completed Module 1: Understanding Artificial Intelligence (AI).\n\n"
            "Key takeaway: AI is a capable assistant, but you are the educator. Your professional "
            "judgment, care for students, and understanding of Ethiopian classrooms ensure AI "
            "serves meaningful learning.\n\n"
            "You can return to the Main Menu, ask your AI Tutor questions, or review the module anytime."
        ),
        "lessons": [
            # ---------------------------------------------------------------
            # Module 1: Understanding Artificial Intelligence (AI)
            # ---------------------------------------------------------------
            {
                "id": "lesson_1",
                "title": "Module 1: Understanding Artificial Intelligence (AI)",
                "image_file": "mod1_obj.jpg",
                "steps": [
                    {
                        "step_index": 0,
                        "title": "Introduction to AI for Teachers in Ethiopia",
                        "texts": [
                            "Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia",
                            f"Course description\n{COURSE_DESCRIPTION}",
                            f"Learning objectives\n{LEARNING_OBJECTIVES}",
                        ],
                    },
                    {
                        "step_index": 1,
                        "title": "Section 1: What is Artificial Intelligence?",
                        "image_file": "mod1_obj.jpg",
                        "texts": [
                            "Section 1: What is Artificial Intelligence?",
                        ],
                        "question": "Q: What is AI?",
                        "prompt_note": "Take a moment to type your answer or thoughts about what AI means to you below:",
                        "model_answer": (
                            "A: Artificial Intelligence (AI) is a technology that enables computers and machines "
                            "to perform tasks that normally require human intelligence, such as learning from information, "
                            "recognizing patterns, understanding language and generating content."
                        ),
                    },
                    {
                        "step_index": 2,
                        "title": "Section 1: Artificial Intelligence in Everyday Life",
                        "image_file": "mod1_everyday_ai.jpg",
                        "texts": [
                            "Section 1: Artificial Intelligence\n\n"
                            "Example of AI in Everyday Life: Artificial Intelligence (AI) is already part of our everyday lives. "
                            "It helps us perform tasks more easily, find information, communicate, and make decisions. "
                            "For example, smartphones recognize our voices, Google Maps suggests routes, translation tools translate "
                            "languages, ChatGPT answers questions, and some systems recognize faces in photographs. "
                            "These examples show how AI makes everyday activities easier, faster, and more convenient."
                        ],
                        "question": "Q: For what purposes do you use AI in your daily life?",
                        "prompt_note": "Type your answer below (e.g. search, translation, writing, maps):",
                        "feedback": (
                            "Thank you for sharing! AI tools are already part of our everyday lives, making activities "
                            "easier, faster, and more convenient."
                        ),
                    },
                    {
                        "step_index": 3,
                        "title": "Section 2: Overview of AI in Education",
                        "image_files": ["mod1_education.jpg", "mod1_opportunities.jpg"],
                        "texts": [
                            "Section 2: Overview of AI in Education\n\n"
                            "Artificial Intelligence (AI) is changing how teachers teach, how students learn, and how schools are managed. "
                            "It can help teachers prepare lesson plans, develop learning materials, create assessments, and provide feedback. "
                            "It can also support students through personalized learning, explanations, and access to educational resources. "
                            "For school leaders, AI can help organize information, analyze school data, and support decision-making. "
                            "When used responsibly, AI can make education more engaging, inclusive, and effective."
                        ],
                    },
                ],
                "closing": MODULE_1_CLOSING,
                "body": [
                    "Section 1: What is Artificial Intelligence?\n\n"
                    "Artificial Intelligence (AI) is a technology that enables computers and machines to perform tasks "
                    "that normally require human intelligence, such as learning from information, recognizing patterns, "
                    "understanding language and generating content.",
                    "Section 1: Examples of AI in Everyday Life:\n"
                    "Smartphones recognize our voices, Google Maps suggests routes, translation tools translate languages, "
                    "ChatGPT answers questions, and systems recognize faces in photographs.",
                    "Section 2: Overview of AI in Education:\n"
                    "AI helps teachers prepare lesson plans, develop learning materials, create assessments, and provide feedback. "
                    "It also supports personalized learning and school management.",
                ],
                "quiz": [
                    {
                        "id": "q1",
                        "question": "1. What is Artificial Intelligence?",
                        "options": {
                            "A": "A computer programming language",
                            "B": "Technology that enables computers to perform tasks requiring human-like intelligence",
                            "C": "A type of internet connection",
                        },
                        "correct": "B",
                        "explanation": (
                            "Correct! Artificial Intelligence is technology that enables computers and machines "
                            "to perform tasks requiring human-like intelligence."
                        ),
                        "hint": (
                            "Think about what defines AI: it is not just programming or an internet connection, "
                            "but technology that performs tasks normally requiring human intelligence."
                        ),
                    },
                    {
                        "id": "q2",
                        "question": "2. Which of the following is an example of Generative AI?",
                        "options": {
                            "A": "ChatGPT generating a lesson plan",
                            "B": "A calculator adding numbers",
                            "C": "A light switch turning on",
                        },
                        "correct": "A",
                        "explanation": (
                            "Correct! Generative AI creates new content, such as ChatGPT generating lesson plans, "
                            "reading passages, or quizzes."
                        ),
                        "hint": (
                            "Generative AI creates and produces new text or content, unlike standard calculators or simple light switches."
                        ),
                    },
                    {
                        "id": "q3",
                        "question": "3. Can AI-generated information always be trusted?",
                        "options": {
                            "A": "Yes, always",
                            "B": "No, teachers must verify it",
                            "C": "Only information written in English",
                        },
                        "correct": "B",
                        "explanation": (
                            "Correct! AI can sometimes make mistakes or produce inaccurate information. "
                            "Teachers must always verify and review AI outputs."
                        ),
                        "hint": (
                            "Remember the core teacher responsibility: AI can hallucinate or make errors, "
                            "so educators must always check and verify content."
                        ),
                    },
                ],
            },
        ],
    }
}

# ---------------------------------------------------------------------------
# Curriculum Query Helpers
# ---------------------------------------------------------------------------

def list_units() -> List[str]:
    return list(UNITS.keys())


def get_unit(unit_id: str = DEFAULT_UNIT_ID) -> Optional[dict]:
    return UNITS.get(unit_id)


def list_lessons(unit_id: str = DEFAULT_UNIT_ID) -> List[str]:
    unit = get_unit(unit_id)
    if not unit:
        return []
    return [l["id"] for l in unit["lessons"]]


def get_lesson(unit_id: str = DEFAULT_UNIT_ID, lesson_index_or_id: Any = 0) -> Optional[dict]:
    unit = get_unit(unit_id)
    if not unit or "lessons" not in unit:
        return None
    lessons = unit["lessons"]
    if isinstance(lesson_index_or_id, int):
        if 0 <= lesson_index_or_id < len(lessons):
            return lessons[lesson_index_or_id]
        return None
    for l in lessons:
        if l["id"] == str(lesson_index_or_id):
            return l
    return None


def get_quiz_questions(unit_id: str = DEFAULT_UNIT_ID, lesson_index_or_id: Any = 0) -> List[dict]:
    lesson = get_lesson(unit_id, lesson_index_or_id)
    if not lesson:
        return []
    quiz = lesson.get("quiz")
    if isinstance(quiz, list):
        return quiz
    elif isinstance(quiz, dict):
        return [quiz]
    return []


def get_quiz(unit_id: str = DEFAULT_UNIT_ID, lesson_index_or_id: Any = 0, question_idx: int = 0) -> Optional[dict]:
    questions = get_quiz_questions(unit_id, lesson_index_or_id)
    if 0 <= question_idx < len(questions):
        return questions[question_idx]
    return None


def total_lessons(unit_id: str = DEFAULT_UNIT_ID) -> int:
    unit = get_unit(unit_id)
    if not unit:
        return 0
    return len(unit.get("lessons", []))


def is_valid_option(unit_id: str, lesson_id: Any, option: str, question_idx: int = 0) -> bool:
    quiz = get_quiz(unit_id, lesson_id, question_idx)
    if not quiz:
        return False
    clean = option.strip().upper()
    return clean in quiz["options"] or option.strip() in quiz["options"]


def check_answer(unit_id: str, lesson_id: Any, selected: str, question_idx: int = 0) -> dict:
    quiz = get_quiz(unit_id, lesson_id, question_idx)
    if not quiz:
        raise ValueError(f"No quiz found for unit={unit_id!r} lesson={lesson_id!r} idx={question_idx}")
    clean = selected.strip().upper()
    correct_answer = quiz["correct"]
    is_correct = (clean == correct_answer) or (selected.strip() == correct_answer)
    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": quiz.get("explanation", ""),
        "hint": quiz.get("hint", ""),
    }


def quiz_as_context(unit_id: str, lesson_id: Any) -> str:
    questions = get_quiz_questions(unit_id, lesson_id)
    if not questions:
        return ""
    blocks = []
    for q in questions:
        options = "; ".join(f"{key}) {text}" for key, text in q["options"].items())
        blocks.append(f"QUIZ QUESTION: {q['question']}\nOPTIONS: {options}")
    return "\n\n".join(blocks)


def lesson_as_context(unit_id: str, lesson_id: Any) -> str:
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
    if 0 <= index < len(ASSESSMENT):
        return ASSESSMENT[index]
    return None
