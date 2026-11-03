"""
bot/ai_tutor.py

AI Pedagogical Tutor backed by the Google Gemini API.
Features:
1. Dynamic model resolution and multi-model fallback (gemini-1.5-flash, gemini-2.0-flash, gemini-1.5-pro).
2. Module-Aware Context: Recognizes whatever module the teacher is on and elaborates on it.
3. Systematic Pedagogical Guardrail: Strictly enforces the course domain without requiring an external vector DB.
4. Resilient REST and SDK invocation with zero silent crashes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import httpx

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

DEFAULT_MODEL = "gemini-1.5-flash"
FALLBACK_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]

_MAX_ANSWER_WORDS = 130
_MAX_OUTPUT_TOKENS = 500


def _get_gemini_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def build_rag_context() -> str:
    """Flatten all course content into a compact text reference for the model."""
    lines = []
    for unit in curriculum.UNITS.values():
        lines.append(f"UNIT: {unit['id']} - {unit['title']}")
        lines.append(f"Summary: {unit['summary']}")
        for lesson in unit.get("lessons", []):
            lines.append(f"MODULE: {lesson.get('title')}")
            for paragraph in lesson.get("body", []):
                lines.append(paragraph)
        lines.append("")
    return "\n".join(lines).strip()


def _build_system_instruction(section: str = "", module_title: str = "") -> str:
    current_module_label = module_title.strip() if module_title else "AI for Teaching and Learning"

    return f"""You are the expert AI Pedagogical Tutor for Ethiopian educators taking the course: "AI for Teaching and Learning (Ethiopian Educators Edition)" by EdTech Hub.

CURRENT ACTIVE MODULE / TOPIC:
{current_module_label}

CURRENT MODULE REFERENCE MATERIAL:
{section if section else 'General Course Curriculum'}

FULL COURSE SYLLABUS REFERENCE:
{build_rag_context()}

STRICT SYSTEMATIC GUARDRAILS & PEDAGOGICAL RULES:
1. IN-SCOPE DOMAIN:
   You strictly answer questions about:
   - The teacher's current module ({current_module_label})
   - Educational AI tools and prompt engineering (5-Part Prompt Formula)
   - Ethiopian classroom realities (50+ students, low connectivity, shared devices, chalkboard transcription)
   - 5-step lesson planning, formative assessment (Evidence to Action), Universal Design for Learning (UDL), and ethical safeguards / student privacy.

2. MODULE ELABORATION:
   When answering questions related to teaching or this course, elaborate clearly and practically. Tie your answer directly to {current_module_label} and offer realistic, low-resource Ethiopian classroom examples.

3. OUT-OF-SCOPE REFUSAL (GUARDRAIL):
   If the user asks questions completely unrelated to teaching, education, or AI pedagogy (e.g., general trivia, entertainment, celebrity gossip, software development unrelated to education, political debates, sports news, cryptocurrency, or off-topic homework solving):
   DO NOT answer the off-topic query. Politely decline and guide them back with this exact educational guardrail:
   "I am your AI Tutor dedicated specifically to the 'AI for Teaching and Learning' course. I can only assist with pedagogical strategies and your current module ({current_module_label}). Feel free to ask any question about this lesson or how to use AI in your classroom!"

4. TONE & FORMATTING:
   - Warm, respectful, encouraging, and professional.
   - Keep answers concise (under {_MAX_ANSWER_WORDS} words) in clear plain text suitable for WhatsApp.
   - Do NOT use aggressive or childish emojis.
"""


def _answer_sync(question: str, section: str, module_title: str) -> str:
    """Synchronous Gemini SDK call with model fallback."""
    api_key = _get_gemini_api_key()
    if not api_key:
        return "The AI tutor is not configured yet. Ask your administrator to set GEMINI_API_KEY."

    if not genai:
        raise RuntimeError("genai library not available")

    genai.configure(api_key=api_key)
    system_inst = _build_system_instruction(section, module_title)

    preferred_model = os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]

    for model_name in models_to_try:
        if model_name == "gemini-2.5-flash":
            model_name = DEFAULT_MODEL
        try:
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_inst,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=_MAX_OUTPUT_TOKENS,
                ),
            )
            response = model.generate_content(question)
            text = (response.text or "").strip()
            if text:
                return text
        except Exception as err:
            logger.warning("Gemini SDK model %s failed: %s", model_name, err)

    raise RuntimeError("All Gemini SDK models failed")


async def _answer_rest(question: str, section: str, module_title: str) -> str:
    """Direct REST call to Gemini API using httpx (zero SDK dependency, robust fallback)."""
    api_key = _get_gemini_api_key()
    if not api_key:
        return "The AI tutor is not configured yet. Ask your administrator to set GEMINI_API_KEY."

    system_inst = _build_system_instruction(section, module_title)
    payload = {
        "contents": [
            {
                "parts": [{"text": question}]
            }
        ],
        "system_instruction": {
            "parts": [{"text": system_inst}]
        },
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": _MAX_OUTPUT_TOKENS,
        }
    }

    preferred_model = os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]

    async with httpx.AsyncClient(timeout=25.0) as client:
        for model_name in models_to_try:
            if model_name == "gemini-2.5-flash":
                model_name = DEFAULT_MODEL
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            text = parts[0].get("text", "").strip()
                            if text:
                                return text
                else:
                    logger.warning("Gemini REST model %s returned HTTP %s: %s", model_name, resp.status_code, resp.text[:200])
            except Exception as e:
                logger.warning("Gemini REST model %s request exception: %s", model_name, e)

    return "I am your AI Tutor. I couldn't reach the service right now, but feel free to ask your question again in a moment!"


async def answer_question(question: str, section: str = "", module_title: str = "") -> str:
    """
    Answer a user's free-text question with module awareness and systematic guardrails.
    Never crashes or exposes raw stack traces.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set")
        return "The AI tutor is not configured yet. Ask your administrator to set GEMINI_API_KEY in Vercel."

    # Try SDK first if available, then fallback to REST
    try:
        if genai is not None:
            return await asyncio.to_thread(_answer_sync, question, section, module_title)
    except Exception as sdk_err:
        logger.warning("Gemini SDK attempt failed: %s. Falling back to direct REST.", sdk_err)

    try:
        return await _answer_rest(question, section, module_title)
    except Exception as rest_err:
        logger.error("Gemini REST attempt also failed: %s", rest_err, exc_info=True)
        return "Sorry, the AI tutor hit a momentary snag. Please try asking your question again."
