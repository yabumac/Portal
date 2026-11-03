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
COURSE_TITLE = "AI for Teaching and Learning (Ethiopian Educators Edition)"

# Intro Media Assets
INTRO_VIDEO_FILENAME = "vid_01_welcome.mp4"
INTRO_LOGO_FILENAME = "logo.png"

BOT_INTRO = (
    "Welcome to AI for Teaching and Learning (Ethiopian Educators Edition).\n\n"
    "This course equips Ethiopian teachers to use Artificial Intelligence practically, "
    "thoughtfully, and ethically in real classroom settings—including large classes, "
    "shared devices, and offline environments.\n\n"
    "Please watch the short introductory video below to review the four course objectives.\n\n"
    "Select an option below to begin:"
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
            "Congratulations on completing AI for Teaching and Learning.\n\n"
            "Key takeaway: AI is a capable assistant, but you are the educator. Your professional "
            "judgment, care for students, and understanding of Ethiopian classrooms ensure AI "
            "serves meaningful learning.\n\n"
            "You can revisit any module or ask your AI Tutor questions anytime."
        ),
        "lessons": [
            # ---------------------------------------------------------------
            # Module 1
            # ---------------------------------------------------------------
            {
                "id": "lesson_1",
                "title": "Module 1: AI Basics and The Teacher as Editor",
                "video_file": "vid_02_basics.mp4",
                "image_file": "img_02_scenario.png",
                "caption": "Video: Pattern Recognition, Generative AI and The Teacher as Editor (0:33-0:49)",
                "body": [
                    "Module 1: AI Basics and The Teacher as Editor\n\n"
                    "Artificial Intelligence (AI) enables computers to recognize patterns across large datasets "
                    "and generate text, images, or audio responses based on probabilities.",
                    "Common Generative AI Categories for Educators:\n"
                    "1. Conversational Chatbots (ChatGPT, Gemini, Claude): Text assistants for drafting lesson plans and explanations.\n"
                    "2. Visual Generators: Create diagrams, charts, and instructional illustrations.\n"
                    "3. Audio and Voice Tools: Speech-to-text transcription and read-aloud support.",
                    "Core Principle - The Teacher as Editor:\n"
                    "AI is an assistant, never a substitute for educator oversight. Your professional judgment "
                    "must guide every instructional, grading, and pedagogical decision.\n\n"
                    "Classroom Decision Example:\n"
                    "When grading 40 student papers, use AI to draft initial feedback suggestions, but review, "
                    "calibrate, and finalize every assessment yourself. Never delegate grading authority entirely to AI.",
                ],
                "quiz": {
                    "question": "What does Generative AI actually do when responding to a teacher prompt?",
                    "options": {
                        "A": "It thinks with human consciousness and emotional reasoning.",
                        "B": "It recognizes patterns in training data to predict useful responses.",
                        "C": "It searches a fixed, static textbook index.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. Generative AI is a pattern recognition and prediction engine. "
                        "Because it predicts likely answers rather than understanding truth, teacher review is essential."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 2
            # ---------------------------------------------------------------
            {
                "id": "lesson_2",
                "title": "Module 2: The 5-Part Teacher Prompt Formula",
                "video_file": "vid_03_prompts.mp4",
                "image_file": "img_03_prompt_formula.png",
                "caption": "Video: The 5-Part Teacher Prompt Formula (2:22-2:41)",
                "body": [
                    "Module 2: Writing Effective Teacher Prompts\n\n"
                    "A prompt is the instruction you give an AI tool. Clear, structured prompts produce high-quality, "
                    "usable classroom materials on the first attempt.",
                    "The 5-Part Prompt Formula:\n"
                    "1. Role: Who should the AI act as? (e.g., 'Act as an experienced Grade 6 Ethiopian science teacher.')\n"
                    "2. Context and Audience: Who are your students? (e.g., 'Class of 55 students with developing English literacy.')\n"
                    "3. Task: What specific material do you need? (e.g., 'Design an interactive 20-minute group activity.')\n"
                    "4. Constraints: What local conditions apply? (e.g., 'No lab equipment, using local garden leaves and simple vocabulary.')\n"
                    "5. Output Format: How should it be structured? (e.g., 'Numbered steps with a 3-question student check.')",
                    "Prompt Refinement:\n"
                    "Treat AI as a conversational partner. If the first output is too long or complex, reply: "
                    "'Shorten to 150 words and use simpler terminology suitable for Grade 6.'",
                ],
                "quiz": {
                    "question": "Which set represents the 5 core elements of the teacher prompt formula?",
                    "options": {
                        "A": "Length, Speed, Grammar, Vocabulary, Tone",
                        "B": "Role, Context, Task, Constraints, Output Format",
                        "C": "Subject, Date, Grade, Score, Textbook",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. Role, Context, Task, Constraints, and Output Format guarantee that "
                        "AI outputs directly match your learners and classroom resources."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 3
            # ---------------------------------------------------------------
            {
                "id": "lesson_3",
                "title": "Module 3: AI in Ethiopian Classrooms (Offline and Low-Resource)",
                "video_file": "vid_04_context.mp4",
                "image_file": "img_04_ethiopia.png",
                "caption": "Video: Ethiopian Classroom Context and Offline Preparation (0:49-1:06)",
                "body": [
                    "Module 3: Practical Strategies for Low-Connectivity and Large Classes\n\n"
                    "Ethiopian classrooms often feature 50+ students, shared devices, and periodic connectivity. "
                    "AI can dramatically reduce your workload when used for teacher preparation.",
                    "Offline Implementation Methods:\n"
                    "1. Batch Preparation: When internet is available, generate lesson materials, quizzes, and discussion questions for the upcoming week and save them on your phone or notebook.\n"
                    "2. Single Device Delivery: You do not need student computers. Write AI-generated reading passages or word problems directly on the chalkboard.\n"
                    "3. Cooperative Learning Groups: Divide classes into teams of 5 to 6 students to solve challenges collaboratively using a single written prompt.\n"
                    "4. Multilingual Bridging: Use AI to create bilingual vocabulary glossaries (English with Amharic, Afaan Oromoo, or Tigrinya terms) to support language learners.",
                ],
                "quiz": {
                    "question": "How can a teacher in a school without student computers use AI effectively?",
                    "options": {
                        "A": "Wait until individual student devices are funded.",
                        "B": "Prepare materials ahead of time on a personal phone and transcribe them onto the chalkboard.",
                        "C": "Only use AI for administrative reports, never for instructional lessons.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. AI supports educator preparation behind the scenes. A teacher with a single phone "
                        "can prepare interactive group activities for an entirely offline class."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 4
            # ---------------------------------------------------------------
            {
                "id": "lesson_4",
                "title": "Module 4: 5-Step Lesson Planning Workflow",
                "video_file": "vid_05_planning.mp4",
                "image_file": "img_05_workflow.png",
                "caption": "Video: 5-Step Lesson Planning Workflow (1:07-1:40)",
                "body": [
                    "Module 4: 5-Step Lesson Planning Workflow\n\n"
                    "Follow this disciplined sequence when planning lessons with AI:\n\n"
                    "Step 1 - Goal: Identify the specific learning standard from the Ethiopian National Curriculum.\n"
                    "Step 2 - Plan: Ask AI for a structured lesson outline (Warm-up, Direct Teaching, Guided Practice, Wrap-up).\n"
                    "Step 3 - Material: Generate culturally authentic examples, local stories, and exercises.\n"
                    "Step 4 - Adapt: Structure activities for whole-class engagement, small groups, or independent practice.\n"
                    "Step 5 - Review: Verify factual correctness, timing feasibility, and curriculum alignment.",
                    "Professional Standard:\n"
                    "Never take an AI-generated lesson directly into class without review. Verify that times, "
                    "prerequisites, and local examples are accurate for your school.",
                ],
                "quiz": {
                    "question": "What is the teacher's most critical responsibility during Step 5 (Review)?",
                    "options": {
                        "A": "Check that the lesson was generated in under thirty seconds.",
                        "B": "Confirm accuracy, curriculum alignment, and feasibility for your classroom.",
                        "C": "Ensure all standard textbook exercises are replaced.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. The educator is the instructional designer. Reviewing ensures every lesson "
                        "meets national curriculum standards and fits your students' current capabilities."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 5
            # ---------------------------------------------------------------
            {
                "id": "lesson_5",
                "title": "Module 5: Formative Assessment and Evidence to Action",
                "video_file": "vid_06_assessment.mp4",
                "image_file": "img_06_assessment.png",
                "caption": "Video: Formative Assessment and Evidence to Action (1:41-2:08)",
                "body": [
                    "Module 5: Formative Assessment and Evidence to Action\n\n"
                    "Formative assessment informs instruction during learning rather than at the end.",
                    "The 3-Stage Assessment Cycle:\n"
                    "1. Generate: Prompt AI to draft exit tickets, short check questions, and diagnostic rubrics.\n"
                    "2. Review: Ensure questions assess deep understanding rather than mere memorization.\n"
                    "3. Evidence to Action: Identify common student errors and ask AI for targeted re-teaching ideas, alternative analogies, or guided peer activities.\n\n"
                    "Guiding Rule: AI informs, but the teacher decides.",
                ],
                "quiz": {
                    "question": "What is the primary role of AI in formative classroom assessment?",
                    "options": {
                        "A": "Grading papers and submitting final marks without teacher check.",
                        "B": "Rapidly drafting assessment checks and proposing re-teaching strategies for student misconceptions.",
                        "C": "Replacing teacher evaluations with automated multiple-choice scoring.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. AI helps formulate diagnostic questions and suggests pedagogical responses "
                        "when students struggle, while the teacher maintains full decision-making control."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 6
            # ---------------------------------------------------------------
            {
                "id": "lesson_6",
                "title": "Module 6: Differentiated and Inclusive Learning (UDL)",
                "video_file": None,
                "image_file": "img_07_collaboration.png",
                "caption": "Infographic: Universal Design for Learning in Collaborative Classrooms",
                "body": [
                    "Module 6: Differentiated and Inclusive Learning\n\n"
                    "Universal Design for Learning (UDL) ensures every student can access challenging content, "
                    "regardless of English proficiency or learning speed.",
                    "Three Core UDL Principles with AI:\n"
                    "1. Multiple Means of Representation: Generate simplified summaries, visual analogies, and bilingual glossaries.\n"
                    "2. Multiple Means of Engagement: Connect abstract topics to local community contexts (agriculture, markets, sports).\n"
                    "3. Multiple Means of Expression: Let students show understanding through writing, oral presentations, or peer diagrams.",
                    "3-Tier Differentiation Prompt:\n"
                    "'Create 3 versions of this reading passage:\n"
                    "- Tier 1: Simplified sentence structure and key vocabulary definitions.\n"
                    "- Tier 2: Standard grade-level text.\n"
                    "- Tier 3: Extension questions requiring analytical application.'",
                ],
                "quiz": {
                    "question": "How does AI support Universal Design for Learning in diverse classrooms?",
                    "options": {
                        "A": "By creating entirely separate syllabi for every individual student.",
                        "B": "By rapidly drafting tiered versions of content while maintaining rigorous standards.",
                        "C": "By lowering academic expectations for students with developing language skills.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. AI allows teachers to generate tiered texts and multiple access points quickly, "
                        "ensuring all students work toward the same high-level competency."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 7
            # ---------------------------------------------------------------
            {
                "id": "lesson_7",
                "title": "Module 7: Responsible AI, Privacy and Final Action Plan",
                "video_file": "vid_07_principles.mp4",
                "image_file": "img_08_principles.png",
                "caption": "Video: 5 Key Principles and Capstone Action Plan (2:58-3:07)",
                "body": [
                    "Module 7: Responsible AI, Student Privacy, and Ethics\n\n"
                    "AI safety and ethics require active teacher vigilance:\n\n"
                    "1. Student Privacy: Never input student names, ID numbers, or personal identifying information into commercial AI tools.\n"
                    "2. Verification: AI models can generate plausible-sounding falsehoods (hallucinations). Always verify facts against official curriculum textbooks.\n"
                    "3. Cultural Alignment: Check AI outputs for cultural relevance and fairness for Ethiopian contexts.\n"
                    "4. Digital Equity: Ensure students without home computers or internet are never disadvantaged.",
                    "The 5 Guiding Principles:\n"
                    "Understand -> Protect -> Align -> Review -> Adapt.\n\n"
                    "Action Step: Start with one lesson plan, one formative exit check, and one reflection this week.",
                ],
                "quiz": {
                    "question": "What is the non-negotiable rule regarding student privacy when using public AI tools?",
                    "options": {
                        "A": "Student names may be entered if grades are left out.",
                        "B": "Never enter student names, identification numbers, or private details into public AI tools.",
                        "C": "Personal information is permitted if the tool states it is for education.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct. Student privacy is paramount. Always use anonymized, generic descriptions "
                        "(e.g., 'Grade 6 student') when prompting AI systems."
                    ),
                },
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


def get_quiz(unit_id: str = DEFAULT_UNIT_ID, lesson_index_or_id: Any = 0) -> Optional[dict]:
    lesson = get_lesson(unit_id, lesson_index_or_id)
    if not lesson:
        return None
    return lesson.get("quiz")


def total_lessons(unit_id: str = DEFAULT_UNIT_ID) -> int:
    unit = get_unit(unit_id)
    if not unit:
        return 0
    return len(unit.get("lessons", []))


def is_valid_option(unit_id: str, lesson_id: Any, option: str) -> bool:
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return False
    clean = option.strip().upper()
    return clean in quiz["options"] or option.strip() in quiz["options"]


def check_answer(unit_id: str, lesson_id: Any, selected: str) -> dict:
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        raise ValueError(f"No quiz found for unit={unit_id!r} lesson={lesson_id!r}")
    clean = selected.strip().upper()
    correct_answer = quiz["correct"]
    is_correct = (clean == correct_answer) or (selected.strip() == correct_answer)
    return {
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": quiz.get("explanation", ""),
    }


def quiz_as_context(unit_id: str, lesson_id: Any) -> str:
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return ""
    options = "; ".join(f"{key}) {text}" for key, text in quiz["options"].items())
    return f"QUIZ QUESTION: {quiz['question']}\nOPTIONS: {options}"


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
