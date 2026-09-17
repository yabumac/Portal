"""
bot/ai_tutor.py

AI Tutor backed by the Gemini API (google-generativeai SDK).

Simple RAG approach
-------------------
The whole curriculum is flattened into a plain-text context block (see
build_rag_context). On top of that, the caller can pass a `section` string -
the CURRENT lesson or quiz the user is looking at - which is injected as the
most-relevant context. That way the tutor always knows exactly where the
student is in the course.

For a larger curriculum, replace the flat context with real retrieval
(embeddings + a vector store) and inject only the top-k matching chunks.

Config (env vars):
    GEMINI_API_KEY - required
    GEMINI_MODEL   - optional, default "gemini-2.5-flash"

Out-of-scope questions (politics, general trivia, etc.) are rejected by the
system prompt so the tutor stays on-topic.
"""

import asyncio
import logging
import os

import google.generativeai as genai

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_MAX_ANSWER_WORDS = 150
_MAX_OUTPUT_TOKENS = 600


def build_rag_context() -> str:
    """Flatten all course content into a compact text context for the model."""
    lines = []
    for unit in curriculum.UNITS.values():
        lines.append(f"UNIT: {unit['id']} - {unit['title']}")
        lines.append(f"Summary: {unit['summary']}")
        for lesson in unit["lessons"]:
            for paragraph in lesson["body"]:
                lines.append(paragraph)
        lines.append("")
    return "\n".join(lines).strip()


SYSTEM_PROMPT_TEMPLATE = f"""
You are the AI Tutor for "AI for Educators", an EdTech Hub teacher-training
course delivered over WhatsApp.

Rules:
1. Answer ONLY using the COURSE CONTEXT below. If the context does not contain
   the answer, say: "I don't have that in the course material yet."
2. If a CURRENT SECTION is provided below, it is what the user is reading or
   doing right now - weight it most heavily.
3. Be concise and educational: at most {_MAX_ANSWER_WORDS} words, plain text.
   No markdown, no bullet symbols, no emojis.
4. Do not answer questions unrelated to the course (general trivia, coding
   help, news, etc.) - redirect back to the course material.
5. Keep the tone friendly and encouraging, like a mentor for teachers.

COURSE CONTEXT:
{{course_context}}
"""


def _build_system_instruction(section: str) -> str:
    instruction = SYSTEM_PROMPT_TEMPLATE.format(
        course_context=build_rag_context()
    )
    if section:
        instruction += (
            "\n\nCURRENT SECTION (user is looking at this right now, most relevant):\n"
            f"{section}\n"
            + "-" * 40
        )
    return instruction


def _answer_sync(question: str, section: str) -> str:
    """Blocking Gemini call (wrapped into a thread by answer_question)."""
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=_build_system_instruction(section),
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
        ),
    )
    response = model.generate_content(question)
    text = (response.text or "").strip()
    return text if text else "I could not find an answer to that in the course material."


async def answer_question(question: str, section: str = "") -> str:
    """
    Answer a user's free-text question, with the full course context plus the
    optional `section` string (current lesson / quiz block) injected.
    Never raises: returns a friendly fallback message on any failure.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set")
        return "The AI tutor is not configured yet. Ask your administrator to set GEMINI_API_KEY."

    try:
        return await asyncio.to_thread(_answer_sync, question, section)
    except Exception as exc:  # noqa: BLE001 - never let AI failures crash the webhook
        logger.error("Gemini call failed: %s", exc, exc_info=True)
        return "Sorry, the AI tutor hit a snag. Please try again in a moment."