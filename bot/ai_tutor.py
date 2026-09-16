"""
bot/ai_tutor.py

AI Tutor backed by the Gemini API (google-generativeai SDK).

Simple RAG approach
-------------------
At import time the whole curriculum is flattened into one plain-text context
block (see build_rag_context). That context is injected into the model as a
system instruction, so every free-text question is answered using ONLY the
course material. For a larger curriculum, replace the flat context with
real retrieval (e.g. embeddings + a vector store) and inject only the top-k
matching chunks.

Config (env vars):
    GEMINI_API_KEY - required
    GEMINI_MODEL   - optional, default "gemini-2.5-flash"

Out-of-scope examples (like "what does Gemini think of X") are rejected by the
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
_GENERATED_MODELS = {}


def build_rag_context() -> str:
    """Flatten all course content into a compact text context for the model."""
    lines = []
    for unit in curriculum.UNITS.values():
        lines.append(f"UNIT: {unit['id']} - {unit['title']}")
        lines.append(f"Summary: {unit['summary']}")
        for lesson in unit["lessons"]:
            lines.append(f"LESSON: {lesson['title']}")
            for paragraph in lesson["body"]:
                lines.append(f"  {paragraph}")
            quiz = lesson.get("quiz")
            if quiz:
                options = "; ".join(
                    f"{letter}) {text}" for letter, text in quiz["options"].items()
                )
                lines.append(
                    f"  QUIZ Q: {quiz['question']} | Options: {options} "
                    f"| Correct: {quiz['correct']}"
                )
        lines.append("")
    return "\n".join(lines).strip()


SYSTEM_PROMPT = f"""
You are the AI Tutor for a WhatsApp-based teacher-training course on digital
literacy for classroom teaching.

Rules:
1. Answer ONLY using the COURSE CONTEXT below. If the context does not contain
   the answer, say: "I don't have that in the course material yet."
2. Be concise and educational: at most {_MAX_ANSWER_WORDS} words, plain text.
   No markdown, no bullet symbols, no emojis.
3. Do not answer questions unrelated to the course (politics, general trivia,
   coding help, etc.) - redirect back to the course material.
4. Keep the tone friendly and encouraging, as a mentor would.

COURSE CONTEXT:
{build_rag_context()}
""".strip()


def _get_model():
    if GEMINI_MODEL not in _GENERATED_MODELS:
        genai.configure(api_key=GEMINI_API_KEY)
        _GENERATED_MODELS[GEMINI_MODEL] = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=600,
            ),
        )
    return _GENERATED_MODELS[GEMINI_MODEL]


def _answer_sync(question: str) -> str:
    """Blocking Gemini call (wrapped into a thread by answer_question)."""
    response = _get_model().generate_content(question)
    text = (response.text or "").strip()
    return text if text else "I could not find an answer to that in the course material."


async def answer_question(question: str) -> str:
    """
    Answer a user's free-text question with the course context injected.
    Never raises: returns a friendly fallback message on any failure.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set")
        return "The AI tutor is not configured yet. Ask your administrator to set GEMINI_API_KEY."

    try:
        return await asyncio.to_thread(_answer_sync, question)
    except Exception as exc:  # noqa: BLE001 - never let AI failures crash the webhook
        logger.error("Gemini call failed: %s", exc, exc_info=True)
        return "Sorry, the AI tutor hit a snag. Please try again in a moment."