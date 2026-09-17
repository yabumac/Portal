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
INTRO_VIDEO_URL = "./media/INTRO_VIDEO.mp4"

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
        "title": "AI for Teaching & Learning",
        "summary": "A comprehensive guide to using AI thoughtfully and practically in your teaching, from lesson planning to assessment.",
        "lessons": [
            {
                "id": "lesson_1",
                "title": "Module 1: Welcome to AI for Teaching",
                "body": [
                    "Welcome to AI for Teaching & Learning! This course helps you use AI thoughtfully and practically in your teaching—even with large classes, limited devices, and connectivity challenges.",
                    "Across 11 short modules, you'll move from foundational AI concepts to hands-on practice. You will learn to write prompts, plan lessons, design activities, support every learner, and use AI responsibly.",
                    "You don't need any prior experience with AI to get started—just curiosity and a willingness to try something new."
                ],
                "media": {
                    "type": "video",
                    "url": "https://example.com/videos/module1-intro.mp4",
                    "caption": "Course Introduction: Welcome to AI for Teaching & Learning"
                },
                "quiz": {
                    "question": "What is the primary role of AI in this course?",
                    "options": {
                        "A": "A replacement for the teacher in the classroom",
                        "B": "A thoughtful teaching assistant to help with planning and activities",
                        "C": "A tool to grade all students automatically without review"
                    },
                    "correct": "B",
                    "explanation": "AI is here to be your thoughtful assistant and save you time, but it is never a replacement for your professional judgment."
                }
            },
            {
                "id": "lesson_2",
                "title": "Module 2: Understanding AI",
                "body": [
                    "Artificial Intelligence (AI) is technology that enables computers to learn from information, recognize patterns, and perform tasks that normally require human intelligence.",
                    "There are different types of AI tools. Chatbots (like ChatGPT) hold text conversations, Image Generators turn descriptions into pictures, and Audio Tools can convert text to speech.",
                    "When you ask a Chatbot a question, it doesn't 'think' like a human. Instead, it predicts the most likely helpful response based on patterns it learned from huge amounts of text."
                ],
                "quiz": {
                    "question": "What does a 'generative AI' chatbot actually do when you ask it something?",
                    "options": {
                        "A": "It recognizes patterns in its training data and predicts a likely, useful response",
                        "B": "It thinks through the problem exactly the way a human would",
                        "C": "It searches a fixed database to copy the exact answer"
                    },
                    "correct": "A",
                    "explanation": "Generative AI doesn't think or search live; it predicts the best response based on learned text patterns."
                }
            },
            {
                "id": "lesson_3",
                "title": "Module 3: AI and the Teacher's Role",
                "body": [
                    "AI is a teaching assistant, not a replacement for the teacher. It can help you draft lessons, brainstorm ideas, create materials, and save time.",
                    "However, your professional judgment must always lead. This is especially true when making decisions about grading, fairness, relationships, and sensitive issues.",
                    "AI can be wrong, biased, or out of context. Always review, edit, and verify its output before using it with your students."
                ],
                "quiz": {
                    "question": "It's exam week and you have 40 papers to grade tonight. What's the right way to use AI?",
                    "options": {
                        "A": "Let the AI grade all 40 exams and just copy the scores over",
                        "B": "Use AI to draft feedback comments, but review and finalize every grade yourself",
                        "C": "Ignore AI entirely because it cannot read student handwriting"
                    },
                    "correct": "B",
                    "explanation": "Let AI help with drafting and routine work, but always keep your professional review on high-stakes decisions like final grades."
                }
            },
            {
                "id": "lesson_4",
                "title": "Module 4: Writing Effective Prompts",
                "body": [
                    "A prompt is the instruction you give an AI tool. Vague prompts give vague results; a good prompt does the heavy lifting.",
                    "Use the 4-Part Formula for great prompts:\n1. Context (Who are you?)\n2. Task (What do you need?)\n3. Audience (Who is it for?)\n4. Format (What shape should the output take?)",
                    "Example of a strong prompt: 'I am a Grade 5 math teacher (Context). Write 5 word problems about fractions (Task). Keep the language simple for multilingual learners (Audience). Provide it as a numbered list (Format).'"
                ],
                "media": {
                    "type": "image",
                    "url": "https://example.com/images/prompt-formula.png",
                    "caption": "The 4-Part Prompt Formula: Context, Task, Audience, Format"
                },
                "quiz": {
                    "question": "Which of these is the BEST example of a strong prompt?",
                    "options": {
                        "A": "Write some quiz questions about the water cycle.",
                        "B": "I teach Grade 6. Write 3 short quiz questions about the water cycle for my ESL students. Output as a numbered list.",
                        "C": "Give me a lesson plan."
                    },
                    "correct": "B",
                    "explanation": "Option B uses the full 4-part formula: Context, Task, Audience, and Format."
                }
            },
            {
                "id": "lesson_5",
                "title": "Module 5: AI for Lesson Planning",
                "body": [
                    "AI can help teachers draft learning objectives, structure lesson plans, and suggest classroom activities.",
                    "One of the best uses of AI is local relevance. Ask AI for examples using Ethiopian contexts—like local crops, currency, geography, or materials—instead of generic or foreign examples.",
                    "Remember: AI helps you plan faster, but you remain responsible for ensuring the lesson is accurate, curriculum-aligned, and age-appropriate."
                ],
                "quiz": {
                    "question": "What should you do with an AI-generated lesson plan before teaching it?",
                    "options": {
                        "A": "It should be reviewed and adapted to fit your students and local context before use",
                        "B": "It's ready to use exactly as written, no review needed",
                        "C": "It should replace your official curriculum entirely"
                    },
                    "correct": "A",
                    "explanation": "AI output is just a first draft. You must always review and adapt it to your specific classroom context."
                }
            },
            {
                "id": "lesson_6",
                "title": "Module 6: Generating Activities",
                "body": [
                    "AI can generate questions, stories, real-world examples, games, and group work. The trick is picking the right activity type for your goal and class size.",
                    "For large classes (50+), favor discussion prompts or quick games that don't need individual materials. For small groups, ask AI for collaborative problem sets.",
                    "Instead of asking for 'a classroom activity', tell the AI your class size, time limit, and available resources so it can tailor the activity to your needs."
                ],
                "quiz": {
                    "question": "When evaluating an AI-generated activity, what is the most important thing to check for?",
                    "options": {
                        "A": "Whether it uses advanced, complex academic language",
                        "B": "Whether it is engaging, clear, and feasible for your specific class size and resources",
                        "C": "Whether the AI took less than 10 seconds to generate it"
                    },
                    "correct": "B",
                    "explanation": "An activity is only useful if it actually works for your specific class size, constraints, and resources."
                }
            },
            {
                "id": "lesson_7",
                "title": "Module 7: Assessment & Feedback",
                "body": [
                    "AI can help you generate quiz questions, rubrics, and answer keys. It can also draft feedback comments that highlight understanding gaps.",
                    "The process is simple: Generate (ask AI for a quiz and rubric), Review (check each question for accuracy against what you taught), and Use & Adapt.",
                    "Never upload student names or personal data when asking AI to help draft feedback."
                ],
                "quiz": {
                    "question": "What is the main benefit of using AI for assessment and feedback tasks?",
                    "options": {
                        "A": "To completely grade students without any teacher involvement",
                        "B": "To eliminate the need for grading rubrics",
                        "C": "To speed up drafting quiz materials and rubrics for the teacher to review"
                    },
                    "correct": "C",
                    "explanation": "AI's role is to speed up the drafting of materials, leaving the final review and grading decisions to you."
                }
            },
            {
                "id": "lesson_8",
                "title": "Module 8: Inclusive Learning",
                "body": [
                    "Every classroom has learners with different abilities, languages, and levels of prior knowledge. AI can help you make one lesson work for many learners without lowering expectations.",
                    "You can ask AI to adapt a reading passage into a simpler version for a struggling reader, or a more challenging version for an advanced student.",
                    "Use the principles of Universal Design for Learning (UDL): offer content in multiple ways (text, images), offer different ways to engage, and allow students to express knowledge differently."
                ],
                "quiz": {
                    "question": "How can AI best support differentiated learning in your classroom?",
                    "options": {
                        "A": "By rewriting texts at different reading levels for struggling and advanced learners",
                        "B": "By forcing all students to learn at the exact same pace",
                        "C": "By removing challenging topics from the curriculum entirely"
                    },
                    "correct": "A",
                    "explanation": "AI is excellent at adapting the complexity of text to meet different learners where they are, without losing the core concepts."
                }
            },
            {
                "id": "lesson_9",
                "title": "Module 9: Ethiopian Classrooms",
                "body": [
                    "Ethiopian classrooms often face large class sizes, limited devices, and low connectivity. These challenges do not mean AI cannot be useful.",
                    "If you have limited devices or internet, use AI on your own phone at home to prepare materials in advance. You can print them or write them on the board during class.",
                    "In multilingual classrooms, you can ask AI to draft materials in simpler language or request translations to support students still building Amharic or English fluency."
                ],
                "quiz": {
                    "question": "If your school has very limited internet access, how should you use AI?",
                    "options": {
                        "A": "Require students to use AI on their personal phones during class",
                        "B": "Prepare AI-assisted materials when you have a connection, and use them offline in class",
                        "C": "You cannot use AI at all until the school gets Wi-Fi"
                    },
                    "correct": "B",
                    "explanation": "AI is a great preparation tool. You can generate and save lessons, quizzes, and activities when you have a connection, and teach offline."
                }
            },
            {
                "id": "lesson_10",
                "title": "Module 10: Responsible & Ethical Use",
                "body": [
                    "AI carries real risks like bias, misinformation, privacy issues, and plagiarism. Human oversight is what keeps its use safe.",
                    "Always verify facts before teaching them, as AI can state incorrect facts very confidently (this is called a 'hallucination').",
                    "Privacy is critical: NEVER enter students' names, grades, or personal details into public AI tools. Treat AI output as a draft, not a finished, original work."
                ],
                "quiz": {
                    "question": "What is the safest approach to student privacy when using AI tools?",
                    "options": {
                        "A": "You should never enter a student's name or personal details into a public AI tool",
                        "B": "It is safe as long as you also include their test scores",
                        "C": "You can share personal data as long as the student is over 13 years old"
                    },
                    "correct": "A",
                    "explanation": "Protect student privacy by keeping all personally identifiable information (PII) out of generative AI tools."
                }
            },
            {
                "id": "lesson_11",
                "title": "Module 11: Hands-on Challenge",
                "body": [
                    "Time to bring it all together! The workflow for using AI is: 1. Plan (choose a lesson) 2. Prompt (use the 4-part formula) 3. Review (check for accuracy) 4. Adapt & Use.",
                    "Every prompt you write and adapt is a chance to save time so you can spend more energy where it matters most: face-to-face with your students.",
                    "Keep experimenting, keep questioning, and keep leading with your expertise. You've completed the course!"
                ],
                "quiz": {
                    "question": "What is the most important step before bringing AI-generated content into your classroom?",
                    "options": {
                        "A": "Submitting the prompt to your school principal for approval",
                        "B": "Reviewing, adapting, and applying your professional judgment to the output",
                        "C": "Making sure the AI generated a very long response"
                    },
                    "correct": "B",
                    "explanation": "Your professional judgment is the most important part of the process. Always review and adapt AI output for your learners."
                }
            }
        ]
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