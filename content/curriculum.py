"""
content/curriculum.py

Curriculum data for "AI for Teaching & Learning (Ethiopian Educators Edition)".
Static declaration of all course content, media links, quizzes, and assessment forms.

Data model:
-----------
UNITS is a dict of unit_id -> unit. Each unit is an ordered list of lessons.
Each lesson maps to an interactive quiz, so progression is:
  lesson_1 -> quiz_1 -> lesson_2 -> quiz_2 -> ... -> unit complete
"""

import os
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Intro assets & Configuration
# ---------------------------------------------------------------------------
DEFAULT_UNIT_ID = "unit_1"
COURSE_TITLE = "AI for Teaching & Learning (Ethiopian Educators Edition)"

# Primary course video (located in /media)
_MAIN_VIDEO = "AI for Teaching and Learning_1080p_caption.mp4"
_BASE_MEDIA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")
_DEFAULT_VIDEO = _MAIN_VIDEO if os.path.exists(os.path.join(_BASE_MEDIA, _MAIN_VIDEO)) else "INTRO_VIDEO.mp4"

INTRO_VIDEO_URL = os.getenv("COURSE_VIDEO_URL") or f"./media/{_DEFAULT_VIDEO}"

BOT_INTRO = (
    "👋 Welcome to AI for Teaching & Learning (Ethiopian Educators Edition)!\n\n"
    "This course helps you use Artificial Intelligence thoughtfully and practically in your teaching—"
    "even with large classes, limited devices, and low connectivity. Whether you teach 50+ students "
    "or share a single smartphone, AI is here to serve as your thoughtful assistant, never a replacement "
    "for your professional judgment.\n\n"
    "▶️ Watch the 33-second welcome video from your instructor, Amina, to see what we will cover.\n\n"
    "Choose an option below to get started:"
)

# ---------------------------------------------------------------------------
# AI Self-Assessment & Reflection Form
# ---------------------------------------------------------------------------
ASSESSMENT = [
    {
        "id": "ai_use",
        "question": "For what purposes or how often do you currently use AI tools in your teaching?",
        "options": {
            "A": "Never tried them yet",
            "B": "Sometimes for ideas & lesson planning",
            "C": "Regularly in my teaching workflow",
        },
    },
    {
        "id": "comfort",
        "question": "How confident do you feel about using AI tools in your classroom?",
        "options": {
            "A": "Not confident yet",
            "B": "Somewhat confident",
            "C": "Very confident",
        },
    },
    {
        "id": "challenge",
        "question": "What is your biggest practical classroom constraint with technology?",
        "options": {
            "A": "Large class sizes (50+ students)",
            "B": "Limited devices or intermittent internet",
            "C": "Knowing how to write effective prompts",
        },
    },
    {
        "id": "goal",
        "question": "What do you most want to achieve from this course?",
        "options": {
            "A": "Practical lesson ideas for Ethiopian classrooms",
            "B": "Time-saving planning & assessment tools",
            "C": "Using AI responsibly, safely, and ethically",
        },
    },
]

# ---------------------------------------------------------------------------
# Course Content: 7 Modules for Ethiopian Educators
# ---------------------------------------------------------------------------
UNITS = {
    "unit_1": {
        "id": "unit_1",
        "title": "AI for Teaching & Learning (Ethiopian Educators Edition)",
        "summary": (
            "A complete, practical guide for Ethiopian educators to use Artificial Intelligence "
            "thoughtfully in teaching, lesson planning, formative assessment, Universal Design "
            "for Learning (UDL), and ethical classroom practice."
        ),
        "complete_message": (
            "🎉 CONGRATULATIONS! 🎉\n\n"
            "You have officially completed AI for Teaching & Learning (Ethiopian Educators Edition)!\n\n"
            "Remember: AI is a fast, capable assistant—but YOU are the teacher. Your professional judgment, "
            "your care for your learners, and your deep knowledge of the Ethiopian classroom are what turn "
            "AI's suggestions into real learning.\n\n"
            "Keep experimenting, keep questioning, and keep leading with your expertise!"
        ),
        "lessons": [
            # ---------------------------------------------------------------
            # Module 1
            # ---------------------------------------------------------------
            {
                "id": "lesson_1",
                "title": "Module 1: AI Basics & The Teacher as Editor",
                "body": [
                    "🧠 Understanding AI & Your Role as an Educator:\n\n"
                    "As your instructor Amina explains, Artificial Intelligence (AI) enables computers to "
                    "learn from information, recognize patterns, and perform tasks like generating lesson ideas, "
                    "drafting exercises, or answering teacher questions.",
                    "Here are the 3 most common types of Generative AI tools you will encounter in your teaching:\n\n"
                    "💬 1. Chatbots (ChatGPT, Gemini, Claude): Text-based assistants that hold a conversation. "
                    "You type a prompt, and the AI predicts the most helpful response based on patterns learned from vast knowledge.\n\n"
                    "🖼️ 2. Image Generators: Tools that turn written descriptions into educational diagrams, charts, and illustrations.\n\n"
                    "🔊 3. Voice & Audio Tools: Tools that convert text into natural-sounding speech or transcribe voice notes into text—"
                    "fantastic for read-alouds, language accessibility, and quick dictation.",
                    "⚠️ The Golden Rule: AI is a capable teaching assistant, NOT a replacement for the educator. "
                    "Your professional judgment must always lead—especially on grading, student fairness, individual relationships, "
                    "and sensitive classroom decisions.",
                    "💬 Real Classroom Decision:\n"
                    "Imagine it is exam week and you have 40 papers to grade tonight. What is the right call?\n"
                    "• Option 1: Use AI to draft feedback comments, but review, calibrate, and finalize every grade yourself.\n"
                    "• Option 2: Let AI grade all 40 papers and just copy the scores over.\n\n"
                    "Always choose Option 1! Handing over final grading removes your professional judgment from high-stakes decisions.",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (0:33–0:49): Pattern Recognition, Generative AI & The Teacher as Editor",
                },
                "quiz": {
                    "question": "What does 'Generative AI' actually do when you ask it a question?",
                    "options": {
                        "A": "It thinks through the problem the exact way a human brain does.",
                        "B": "It recognizes patterns in training data to predict a likely, useful response.",
                        "C": "It looks up the answer in a fixed, unchangeable textbook database.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Spot on! Generative AI is a pattern-recognition and prediction engine, not magic or a human brain. "
                        "It assists your preparation, but you remain the expert editor."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 2
            # ---------------------------------------------------------------
            {
                "id": "lesson_2",
                "title": "Module 2: Writing Effective Teacher Prompts",
                "body": [
                    "✍️ Writing Effective Prompts for the Classroom:\n\n"
                    "A prompt is the instruction you give an AI tool. Vague prompts yield generic, unusable results—"
                    "a well-structured prompt does the heavy lifting for you!",
                    "Here is the proven 5-Part Teacher Prompt Formula for Ethiopian classrooms:\n\n"
                    "1️⃣ Role: Who should the AI act as? (e.g., 'Act as an experienced Ethiopian Grade 5 math teacher.')\n"
                    "2️⃣ Context & Audience: What is your classroom situation and who are the learners? (e.g., 'I teach 50 multilingual students who are beginning English readers.')\n"
                    "3️⃣ Task: What exact output do you need? (e.g., 'Write 5 word problems on fractions.')\n"
                    "4️⃣ Constraints: What local context or resource limits must it follow? (e.g., 'Use everyday Ethiopian contexts like market shopping or sharing injera, with minimal materials.')\n"
                    "5️⃣ Output / Format: What shape should it take? (e.g., 'Format as a numbered list with a step-by-step teacher answer key.')",
                    "❌ Weak Prompt: 'Give me some activities about photosynthesis.'\n\n"
                    "✅ Strong Prompt: 'Act as a Grade 6 Ethiopian science teacher (Role). I teach 55 students in a classroom with no lab equipment and developing English fluency (Context/Audience). Create a 15-minute group activity on photosynthesis (Task) using local schoolyard plants and simple English (Constraints). Format as a 4-step teacher guide with 3 discussion questions (Output).'",
                    "🔁 Pro Tip (Review & Refine):\n"
                    "AI conversation is iterative! Once the AI responds, always ask follow-up prompts to adjust difficulty, shorten passages, or add local analogies.",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (2:22–2:41): The 5-Part Teacher Prompt Formula",
                },
                "quiz": {
                    "question": "Which 5 elements form the ultimate prompt formula for effective classroom outputs?",
                    "options": {
                        "A": "Speed, Length, Grammar, Complexity, Source",
                        "B": "Role, Context & Audience, Task, Constraints, Output Format",
                        "C": "Subject, Due Date, Test Score, Chapter, Difficulty",
                    },
                    "correct": "B",
                    "explanation": (
                        "Exactly right! Role + Context + Task + Constraints + Format ensures the AI tailors its suggestions "
                        "precisely to your students, language levels, and local realities."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 3
            # ---------------------------------------------------------------
            {
                "id": "lesson_3",
                "title": "Module 3: AI in the Ethiopian Classroom Context",
                "body": [
                    "🌍 Real Constraints, Real Solutions:\n\n"
                    "Ethiopian educators often teach in classrooms with 50+ students, shared devices, intermittent connectivity, "
                    "and multilingual learners. These realities do not mean AI cannot help!",
                    "Practical strategies for real school environments:\n\n"
                    "👥 Large Class Sizes (50+ Students): Generate one high-quality story, group discussion prompt, or challenge "
                    "and write it on the chalkboard—zero student devices needed.\n\n"
                    "📱 Limited Devices: Use AI on your personal smartphone or a staff room computer to prepare materials ahead of time, "
                    "then teach completely offline.\n\n"
                    "📶 Low or Intermittent Connectivity: Batch your AI work when connected! Generate lesson plans, exercises, and quizzes "
                    "for the whole week, save templates on your phone, and teach offline.\n\n"
                    "🗣️ Multilingual Classrooms: Ask AI to simplify English reading levels, create bilingual vocabulary glossaries "
                    "(e.g., English-Amharic terms), or generate parallel reading passages.",
                    "💡 Case Study (Selam's Strategy):\n"
                    "Selam teaches Grade 5 in a rural school with 65 students, one staff room computer, and internet only two days a week. "
                    "By batching her planning on connected days and writing group exercises on the blackboard, she delivers AI-enhanced lessons "
                    "all week device-free!",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (0:49–1:06 & 2:41–2:57): Ethiopian Classroom Context & Offline Prep",
                },
                "quiz": {
                    "question": "How can a teacher in a school with 60+ students and no student devices use AI effectively?",
                    "options": {
                        "A": "Wait until every student is given a smartphone before using AI.",
                        "B": "Use AI in advance on a teacher device to prepare materials, then write them on the board for group work.",
                        "C": "Only use AI for administrative paperwork, never for lesson activities.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Spot on! AI supports teacher preparation behind the scenes. A single teacher with one device can generate "
                        "engaging materials that empower an entire offline classroom."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 4
            # ---------------------------------------------------------------
            {
                "id": "lesson_4",
                "title": "Module 4: Lesson Planning & Classroom Activities",
                "body": [
                    "📝 5-Step Lesson Planning Workflow:\n\n"
                    "When using AI as your planning partner, follow the 5-Step Classroom Workflow:\n\n"
                    "1️⃣ Goal: Anchor your lesson in a clear competency from the Ethiopian National Curriculum.\n"
                    "2️⃣ Plan: Ask AI to sketch an engaging timed structure (warm-up, direct instruction, guided practice, wrap-up).\n"
                    "3️⃣ Material: Generate culturally relevant reading passages, worksheets, or word problems using local contexts "
                    "(Ethiopian crops, currency, regional geography).\n"
                    "4️⃣ Adapt for Class Dynamics:\n"
                    "   • Whole Class (50+): Interactive oral questions, choral reading, board challenges.\n"
                    "   • Small Groups (Teams of 4–6): Collaborative problem-solving sets requiring minimal paper.\n"
                    "   • Individual Practice: Differentiated exercises written on the chalkboard.\n"
                    "5️⃣ Review: Act as the Lead Designer! Verify factual accuracy, curriculum alignment, and grade-level feasibility before class.",
                    "🛠️ Tools to Explore:\n"
                    "ChatGPT, Google Gemini, Claude, Canva Magic Studio, or offline SMS bots based on your connectivity.",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (1:07–1:40 & 2:08–2:22): 5-Step Lesson Planning Workflow & Tools",
                },
                "quiz": {
                    "question": "When evaluating an AI-generated lesson plan before class, what is your top priority?",
                    "options": {
                        "A": "Verifying it took less than 10 seconds for the AI to produce.",
                        "B": "Ensuring it is accurate, curriculum-aligned, engaging, and feasible for your classroom resources.",
                        "C": "Making sure it replaces the national curriculum textbook entirely.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct! Speed means nothing if the lesson does not align with your curriculum and classroom reality. "
                        "Your review ensures relevance and feasibility."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 5
            # ---------------------------------------------------------------
            {
                "id": "lesson_5",
                "title": "Module 5: Assessment, Feedback & Evidence-to-Action",
                "body": [
                    "📊 Formative Assessment in 3 Stages:\n\n"
                    "AI saves hours on formative assessment through a 3-Stage Cycle:\n\n"
                    "1️⃣ Generate: Prompt AI to draft multiple-choice checks, short-answer questions, rubrics, and model answers.\n"
                    "2️⃣ Review & Calibrate: Check every question and rubric criteria for fairness, curriculum match, and clarity.\n"
                    "3️⃣ From Evidence to Action: Feed anonymous student error patterns back into AI to identify common misconceptions "
                    "and suggest your Next Teaching Move (e.g., an alternative analogy, peer review, or targeted recap).",
                    "⚖️ The Guiding Principle:\n"
                    "AI Informs • Teacher Decides.\n"
                    "AI helps identify patterns across 50+ papers, but your professional insight determines how to guide each student.",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (1:41–2:08): Formative Assessment & Evidence to Action",
                },
                "quiz": {
                    "question": "What is the primary benefit of using AI for classroom assessment?",
                    "options": {
                        "A": "Allowing the AI to grade and submit student scores without teacher oversight.",
                        "B": "Accelerating drafting of quizzes and rubrics, and identifying learning trends for teacher action.",
                        "C": "Eliminating the need for formative assessment entirely.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Exactly right! AI speeds up the preparation of formative assessments and highlights trends in student errors, "
                        "while you retain complete authority over grading and pedagogical decisions."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 6
            # ---------------------------------------------------------------
            {
                "id": "lesson_6",
                "title": "Module 6: Differentiated & Inclusive Learning (UDL)",
                "body": [
                    "🎯 Supporting Every Learner with Universal Design for Learning (UDL):\n\n"
                    "Every classroom has learners with varied language proficiencies, learning paces, and needs. "
                    "UDL uses AI to make one lesson work for all students without lowering standards:",
                    "1️⃣ Representation: Present core ideas in multiple ways—simplified language, visual descriptions, "
                    "local analogies, bilingual vocabulary lists.\n"
                    "2️⃣ Engagement: Connect topics to students' daily lives and offer choice in tasks.\n"
                    "3️⃣ Expression: Allow learners to demonstrate understanding through writing, speaking, drawing, or demonstration.",
                    "📋 3-Tier Differentiation Prompt Template:\n\n"
                    "'Adapt this reading passage on [Topic] into three levels:\n"
                    "(1) Simplified version with key vocabulary definitions for developing English readers,\n"
                    "(2) Grade-level standard version, and\n"
                    "(3) Extension challenge with real-world application questions for advanced learners.'\n\n"
                    "In minutes, you have differentiated support for all learners in the same 40-minute period!",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video / Graphic: Universal Design for Learning & Inclusive Classroom Strategies",
                },
                "quiz": {
                    "question": "How does AI support Universal Design for Learning (UDL) in mixed-ability classrooms?",
                    "options": {
                        "A": "By creating separate, completely different curriculums for each student.",
                        "B": "By rapidly drafting tiered materials (simplified, on-level, extension) targeting the same core standard.",
                        "C": "By lowering academic expectations for students who struggle with English.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Spot on! UDL maintains high expectations for all learners while providing multiple access points "
                        "(tiered reading, bilingual vocabulary, extension tasks) using AI drafting."
                    ),
                },
            },

            # ---------------------------------------------------------------
            # Module 7
            # ---------------------------------------------------------------
            {
                "id": "lesson_7",
                "title": "Module 7: Responsible & Ethical AI + Final Action Plan",
                "body": [
                    "🛡️ Responsible & Ethical AI in the Classroom:\n\n"
                    "AI is powerful, but carries significant risks that demand active teacher guardianship:\n\n"
                    "🔒 Student Privacy: NEVER input students' full names, IDs, grades, or personal details into public AI tools.\n"
                    "🔍 Misinformation (Hallucinations): AI tools can state incorrect facts with total confidence. Always cross-check facts with your official textbook.\n"
                    "⚖️ Bias & Fairness: AI models can reflect cultural stereotypes or Western-centric assumptions. Review outputs for local Ethiopian cultural fairness.\n"
                    "📝 Academic Integrity: Treat AI output as a draft, and teach students that copying AI text is not original learning.\n"
                    "📶 Digital Equity: Design activities so students without home internet or smartphones are never penalized.",
                    "🎓 Five Key Principles:\n"
                    "Understand ➡️ Protect ➡️ Align ➡️ Review ➡️ Adapt.\n\n"
                    "Start small: one lesson, one resource, one safeguard, and one reflection.",
                ],
                "media": {
                    "type": "video",
                    "url": INTRO_VIDEO_URL,
                    "caption": "▶️ Video Clip (2:58–3:07): 5 Key Principles & Capstone Action Plan",
                },
                "quiz": {
                    "question": "What is the most critical rule regarding student data and public AI tools?",
                    "options": {
                        "A": "Student names are fine to enter as long as test scores are omitted.",
                        "B": "Never enter student names, identification, or personal details into public AI tools.",
                        "C": "Only enter student data if the AI tool claims to be educational.",
                    },
                    "correct": "B",
                    "explanation": (
                        "Correct! Student privacy is absolute and non-negotiable. Always use anonymized, generic descriptions "
                        "(e.g., 'a Grade 5 learner') when prompting AI."
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
    """Return all unit ids in order."""
    return list(UNITS.keys())


def get_unit(unit_id: str) -> Optional[dict]:
    """Return unit dict or None."""
    return UNITS.get(unit_id)


def list_lessons(unit_id: str = DEFAULT_UNIT_ID) -> List[str]:
    """Return all lesson ids for a unit in order."""
    unit = get_unit(unit_id)
    if not unit:
        return []
    return [l["id"] for l in unit["lessons"]]


def get_lesson(unit_id: str = DEFAULT_UNIT_ID, lesson_id: str = "") -> Optional[dict]:
    """Return a single lesson dict or None."""
    unit = get_unit(unit_id)
    if not unit:
        return None
    for l in unit["lessons"]:
        if l["id"] == lesson_id:
            return l
    return None


def get_quiz(unit_id: str = DEFAULT_UNIT_ID, lesson_id: str = "") -> Optional[dict]:
    """Return quiz dict for a lesson or None."""
    lesson = get_lesson(unit_id, lesson_id)
    if not lesson:
        return None
    return lesson.get("quiz")


def total_lessons(unit_id: str = DEFAULT_UNIT_ID) -> int:
    """Return total count of lessons in the unit."""
    unit = get_unit(unit_id)
    if not unit:
        return 0
    return len(unit.get("lessons", []))


def is_valid_option(unit_id: str, lesson_id: str, option: str) -> bool:
    """True if option is one of the valid quiz choices (e.g. A, B, C, or 1, 2)."""
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return False
    clean = option.strip().upper()
    return clean in quiz["options"] or option.strip() in quiz["options"]


def check_answer(unit_id: str, lesson_id: str, selected: str) -> dict:
    """
    Check if the user's answer is correct.
    Returns:
        {"correct": bool, "correct_answer": str, "explanation": str}
    """
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


def quiz_as_context(unit_id: str, lesson_id: str) -> str:
    """Plain-text block of the lesson quiz, used as AI tutor context."""
    quiz = get_quiz(unit_id, lesson_id)
    if not quiz:
        return ""
    options = "; ".join(f"{key}) {text}" for key, text in quiz["options"].items())
    return f"QUIZ QUESTION: {quiz['question']}\nOPTIONS: {options}"


def lesson_as_context(unit_id: str, lesson_id: str) -> str:
    """Plain-text block of an entire lesson, used as AI tutor context."""
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
