"""
bot/ai_tutor.py

Resilient AI Pedagogical Tutor for Ethiopian educators.
Features:
1. Dynamic model discovery: Queries Google Gemini API for valid, active models for the API key.
2. Dual API support: Supports both v1beta and v1 endpoints with multi-model fallback.
3. System instruction & universal inlined prompt fallback.
4. Intelligent Pedagogical Knowledge-Base Engine (Solid Fallback): Guarantees rich, contextual answers even if external API limits or errors occur.
5. Systematic Module-Aware Guardrails: Focuses exclusively on pedagogical strategy and the educator's active module.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Optional

import httpx

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from content import curriculum

logger = logging.getLogger("whatsapp_bot")

DEFAULT_MODEL = "gemini-1.5-flash"
FALLBACK_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]

_MAX_ANSWER_WORDS = 140
_MAX_OUTPUT_TOKENS = 600

# Cache discovered models for 10 minutes
_DISCOVERED_MODELS_CACHE: list[str] = []
_DISCOVERED_CACHE_TIME: float = 0.0


def _get_gemini_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment, stripped of quotes or whitespace."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key.strip().strip('"').strip("'")
    return None


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
   - Educational AI tools and prompt engineering (5-Part Prompt Formula: Role, Context, Task, Constraints, Output Format)
   - Ethiopian classroom realities (50+ students, low connectivity, single phone preparation, chalkboard transcription)
   - 5-step lesson planning (Objective, Hook, Instruction, Practice, Exit Ticket)
   - Formative assessment (Evidence to Action), Universal Design for Learning (UDL), and ethical safeguards / student privacy.

2. MODULE ELABORATION:
   When answering questions related to teaching or this course, elaborate clearly and practically. Tie your answer directly to {current_module_label} and offer realistic, low-resource Ethiopian classroom examples.

3. OUT-OF-SCOPE REFUSAL (GUARDRAIL):
   If the user asks questions completely unrelated to teaching, education, or AI pedagogy (e.g., sports, celebrity gossip, software development unrelated to education, political debates, cryptocurrency, or entertainment):
   DO NOT answer the off-topic query. Politely decline with this exact message:
   "I am your AI Tutor dedicated specifically to the 'AI for Teaching and Learning' course. I can only assist with pedagogical strategies and your current module ({current_module_label}). Feel free to ask any question about this lesson or how to use AI in your classroom!"

4. TONE & FORMATTING:
   - Professional, encouraging, and clear for WhatsApp reading.
   - Keep answers concise (under {_MAX_ANSWER_WORDS} words) in plain text.
   - Do NOT use aggressive or childish emojis.

5. CRITICAL DIRECT RESPONSE RULE:
   - You are chatting directly with an educator on WhatsApp.
   - Output ONLY the final pedagogical answer intended for the teacher.
   - NEVER output internal thinking, chain-of-thought, reasoning scratchpads, checklist items, or drafting evaluations.
   - NEVER output bullet points like '* User Question:', '* Role:', '* Constraint Check:', or '* Drafting:'.
   - Start directly with your pedagogical response text.
"""


# ---------------------------------------------------------------------------
# Solid Pedagogical Knowledge-Base Engine (Guaranteed Fallback & Workaround)
# ---------------------------------------------------------------------------

def _is_off_topic(low_q: str) -> bool:
    """Detect clearly off-topic questions that violate course guardrails."""
    off_topic_patterns = [
        r"\b(football|messi|ronaldo|premier league|manchester|arsenal|champions league)\b",
        r"\b(crypto|bitcoin|ethereum|trading|forex|stock market)\b",
        r"\b(movie|cinema|hollywood|netflix|actor|actress|celebrity)\b",
        r"\b(politics|election|president|prime minister|war in|military)\b",
        r"\b(weather forecast|horoscope|zodiac|gaming|fortnite|gta|playstation)\b",
    ]
    for pat in off_topic_patterns:
        if re.search(pat, low_q):
            return True
    return False


def answer_pedagogy_kb(question: str, section: str = "", module_title: str = "") -> str:
    """
    Intelligent knowledge-base pedagogical responder.
    Guarantees an accurate, structured, high-quality answer grounded in the course curriculum.
    """
    low_q = question.lower().strip()
    active_module = module_title.strip() if module_title else "AI for Teaching and Learning"

    # Guardrail check
    if _is_off_topic(low_q):
        return (
            f"I am your AI Tutor dedicated specifically to the 'AI for Teaching and Learning' course. "
            f"I can only assist with pedagogical strategies and your current module ({active_module}). "
            f"Feel free to ask any question about this lesson or how to use AI in your classroom!"
        )

    # Topic 1: Teacher as Editor / Controller / Authority / Review
    if any(k in low_q for k in ("controller", "control", "editor", "authority", "hallucinat", "fact check", "trust", "review")):
        return (
            f"In {active_module}, the central principle is 'The Teacher as Editor and Controller.'\n\n"
            "Generative AI does not possess pedagogical judgment or factual consciousness—it is a statistical prediction engine. "
            "Therefore, the teacher remains the final controller of the classroom:\n"
            "1. Review every AI draft against your national curriculum standards.\n"
            "2. Verify facts, dates, and localized context before sharing.\n"
            "3. Adjust the difficulty and vocabulary to match your learners.\n\n"
            "AI serves as your preparation assistant, but you maintain full pedagogical authority."
        )

    # Topic 2: 5-Part Formula / Prompting
    if any(k in low_q for k in ("prompt", "formula", "5-part", "5 part", "part", "how to prompt", "instruction", "output format")):
        return (
            "The 5-Part Prompt Formula ensures high-quality classroom outputs from AI:\n\n"
            "1. Role: Who should AI act as? (e.g., 'Grade 7 General Science teacher')\n"
            "2. Context: Who are your learners? (e.g., '55 students in a rural Ethiopian school')\n"
            "3. Task: What should it create? (e.g., 'A 15-minute group discussion activity on plant cells')\n"
            "4. Constraints: Classroom limitations (e.g., 'No devices, chalkboard only, local materials')\n"
            "5. Output Format: Structure of response (e.g., 'Step-by-step numbered instructions').\n\n"
            "Including all 5 elements turns generic responses into classroom-ready materials."
        )

    # Topic 3: Lesson Planning / 5-Step Structure
    if any(k in low_q for k in ("lesson plan", "planning", "5-step", "5 step", "objective", "hook", "guided practice")):
        return (
            "Effective lesson planning with AI follows a 5-step instructional flow:\n\n"
            "1. Learning Objective: Align with grade-level competencies.\n"
            "2. Hook: Prompt AI for a 5-minute curiosity-sparking local riddle or question.\n"
            "3. Direct Instruction: Generate tiered explanations and clear analogies.\n"
            "4. Guided & Independent Practice: Draft group challenges or paired exercises.\n"
            "5. Exit Ticket: Create 2 diagnostic exit questions to check mastery.\n\n"
            "Always tailor the timing and activities to your typical 40-45 minute period."
        )

    # Topic 4: Low-Resource & Offline Preparation / Single Device / Large Classes
    if any(k in low_q for k in ("offline", "low resource", "internet", "connectivity", "phone", "chalkboard", "blackboard", "large class", "50")):
        return (
            "In low-connectivity or high-density Ethiopian classrooms (50+ students), use the 'Batch Preparation' methodology:\n\n"
            "1. Offline Reality: Students do not need devices or internet. The teacher uses a single phone during connectivity hours.\n"
            "2. Advance Drafting: Prompt AI to generate tiered reading passages, vocabulary glossaries, or quiz questions.\n"
            "3. Classroom Delivery: Transcribe exercises onto the chalkboard or assign small peer groups to share a single written prompt.\n\n"
            "This empowers you to deliver modern, differentiated pedagogy completely offline."
        )

    # Topic 5: Formative Assessment / Evidence to Action / Exit Tickets
    if any(k in low_q for k in ("assessment", "formative", "quiz", "evidence", "ticket", "exit", "diagnos", "re-teach")):
        return (
            "Formative assessment is about transforming 'Evidence into Action':\n\n"
            "1. Quick Diagnostics: Prompt AI to create a 2-question exit ticket with plausible distractors that reveal common misconceptions.\n"
            "2. Evidence Collection: Review student answers to see which group grasped the concept and which struggled.\n"
            "3. Action / Re-teaching: Ask AI for an alternative visual metaphor or hands-on activity to re-teach the topic tomorrow.\n\n"
            "The goal is real-time adjustment, not assigning punitive grades."
        )

    # Topic 6: Universal Design for Learning (UDL) / Inclusion / Differentiation
    if any(k in low_q for k in ("udl", "universal design", "differentiat", "inclusion", "struggl", "advanced", "tier", "special")):
        return (
            "Universal Design for Learning (UDL) ensures every student reaches the same competency through multiple means of access:\n\n"
            "1. Tiered Texts: Use AI to take a core reading passage and instantly create 3 versions: simplified vocabulary, standard grade-level, and enriched.\n"
            "2. Multiple Representations: Generate bilingual word banks (e.g., Amharic and English terms) and visual diagram descriptions.\n"
            "3. Multiple Means of Action: Allow learners to demonstrate understanding via oral presentations, chalkboard problem-solving, or drawings."
        )

    # Topic 7: Privacy, Safety, Ethics, and Bias
    if any(k in low_q for k in ("privacy", "safety", "ethic", "bias", "pii", "student name", "data", "protect")):
        return (
            "Student data protection and ethical AI use are foundational:\n\n"
            "1. Never Share PII: Never enter student names, identification numbers, grades, or personal family information into any AI tool.\n"
            "2. Anonymous Personas: Use generic descriptors instead (e.g., 'A Grade 6 student struggling with multi-step word problems').\n"
            "3. Bias Inspection: Check AI suggestions for cultural relevance and ensure they do not reinforce gender or regional stereotypes."
        )

    # Contextual Elaboration based on Active Module
    if section:
        clean_section = "\n".join([line.strip() for line in section.splitlines() if line.strip() and not line.startswith("MODULE:")])[:400]
        return (
            f"Here is pedagogical guidance for your question regarding {active_module}:\n\n"
            f"{clean_section}\n\n"
            "Practical Classroom Application: Remember that AI is most effective when guided by clear constraints "
            "(such as class size, available materials, and curriculum standards). "
            "Feel free to ask a specific question about how to apply this in your classroom!"
        )

    # General course encouragement
    return (
        f"In {active_module}, AI acts as a powerful preparation partner for Ethiopian educators. "
        "You can use it to draft lesson objectives, generate localized examples, create differentiated exercises, "
        "and formulate formative exit tickets. "
        "What specific challenge or classroom activity would you like to explore?"
    )


# ---------------------------------------------------------------------------
# Dynamic Model Discovery & Resilient Gemini Calling
# ---------------------------------------------------------------------------

async def _discover_models(client: httpx.AsyncClient, api_key: str) -> list[str]:
    """
    Query Google Generative Language API to dynamically discover available models for this key.
    Caches results to minimize overhead.
    """
    global _DISCOVERED_MODELS_CACHE, _DISCOVERED_CACHE_TIME
    now = time.time()
    if _DISCOVERED_MODELS_CACHE and (now - _DISCOVERED_CACHE_TIME) < 600:
        return _DISCOVERED_MODELS_CACHE

    endpoints = [
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
    ]

    valid_models = []
    for ep in endpoints:
        try:
            resp = await client.get(ep, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("models", []):
                    methods = item.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        raw_name = item.get("name", "")
                        clean_name = raw_name.replace("models/", "")
                        if clean_name not in valid_models:
                            valid_models.append(clean_name)
                if valid_models:
                    break
        except Exception as e:
            logger.debug("Model discovery exception on %s: %s", ep, e)

    if valid_models:
        _DISCOVERED_MODELS_CACHE = valid_models
        _DISCOVERED_CACHE_TIME = now
        logger.info("Dynamically discovered Gemini models: %s", valid_models[:5])

    return valid_models


def clean_ai_output(text: str) -> str:
    """
    Sanitize model output:
    1. Strips <thought>...</thought> tags if present.
    2. Strips chain-of-thought scratchpads (e.g. * User Question:, * Constraint Check:, * Drafting:).
    3. Extracts final response clean of internal reasoning.
    """
    if not text:
        return ""

    # Strip XML-style thinking or reasoning tags
    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"<reasoning>.*?</reasoning>", "", text, flags=re.DOTALL).strip()

    # Detect scratchpad / reasoning leak markers
    scratchpad_markers = (
        "*   User Question:", "* User Question:",
        "*   Current Module:", "* Current Module:",
        "*   Role:", "* Role:",
        "*   Context:", "* Context:",
        "*   Constraint Check:", "* Constraint Check:",
        "*   Drafting:", "* Drafting:",
        "*   Word Count Check:", "* Word Count Check:",
        "*   Tone Check:", "* Tone Check:",
        "*   Content Check:", "* Content Check:",
    )

    if any(marker in text for marker in scratchpad_markers):
        # 1. Try to extract final quoted text block if present (e.g., "In Module 1, ...")
        quotes = re.findall(r'"([A-Z][^"]{40,})"', text, flags=re.DOTALL)
        if quotes:
            return quotes[-1].strip()

        # 2. Try to extract text under '* Drafting:*'
        drafting_m = re.search(r'\*\s*\*Drafting:\*\s*\n(.*?)(?=\n\s*\*|\Z)', text, flags=re.DOTALL)
        if drafting_m:
            draft_candidate = drafting_m.group(1).strip()
            if draft_candidate:
                return draft_candidate

        # 3. Filter out scratchpad lines
        clean_lines = []
        for line in text.splitlines():
            s = line.strip()
            if s.startswith('*') and any(m.strip('* :') in s for m in scratchpad_markers):
                continue
            clean_lines.append(line)
        cleaned = "\n".join(clean_lines).strip()
        if cleaned:
            return cleaned

    return text.strip()


async def _answer_rest(question: str, section: str, module_title: str) -> str:
    """
    Direct REST call to Gemini API with dynamic model discovery and universal payload fallback.
    If the API is unreachable, falls back to the pedagogical knowledge-base engine.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        return answer_pedagogy_kb(question, section, module_title)

    system_inst = _build_system_instruction(section, module_title)

    payload_primary = {
        "systemInstruction": {
            "parts": [{"text": system_inst}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": question}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": _MAX_OUTPUT_TOKENS,
        }
    }

    payload_universal = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTIONS & PEDAGOGICAL RULES:\n{system_inst}\n\nTEACHER QUESTION:\n{question}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": _MAX_OUTPUT_TOKENS,
        }
    }

    last_error = ""
    async with httpx.AsyncClient(timeout=25.0) as client:
        # Dynamically discover active models for this key
        discovered = await _discover_models(client, api_key)
        preferred_model = os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        
        # Build prioritized list of model names
        models_to_try = []
        if preferred_model in discovered:
            models_to_try.append(preferred_model)
        for m in discovered:
            if m not in models_to_try:
                models_to_try.append(m)
        for m in FALLBACK_MODELS:
            if m not in models_to_try:
                models_to_try.append(m)

        for model_name in models_to_try[:6]:
            for api_version in ("v1beta", "v1"):
                url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model_name}:generateContent?key={api_key}"
                for payload in (payload_primary, payload_universal):
                    try:
                        resp = await client.post(url, json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                valid_parts = []
                                for p in parts:
                                    # Never include thought / internal reasoning parts
                                    if p.get("thought") is True:
                                        continue
                                    txt = p.get("text", "").strip()
                                    if txt:
                                        valid_parts.append(txt)

                                raw_text = "\n".join(valid_parts).strip() if valid_parts else (parts[-1].get("text", "").strip() if parts else "")
                                text = clean_ai_output(raw_text)
                                if text:
                                    return text
                        else:
                            last_error = f"{model_name} ({api_version}) HTTP {resp.status_code}: {resp.text[:120]}"
                    except Exception as e:
                        last_error = f"{model_name} ({api_version}) err: {e}"

    if last_error:
        logger.warning("Gemini REST attempts failed: %s", last_error)
        try:
            from bot import db
            db.log_activity("system", "gemini_api_error", last_error)
        except Exception:
            pass

    # Seamless knowledge-base fallback guarantees 100% answer delivery
    logger.info("Using pedagogical knowledge-base engine for question: %s", question[:60])
    return answer_pedagogy_kb(question, section, module_title)


def _answer_sync(question: str, section: str, module_title: str) -> str:
    """Synchronous Gemini SDK call with model fallback."""
    api_key = _get_gemini_api_key()
    if not api_key:
        return answer_pedagogy_kb(question, section, module_title)

    if not genai:
        raise RuntimeError("genai library not available")

    genai.configure(api_key=api_key)
    system_inst = _build_system_instruction(section, module_title)

    preferred_model = os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]

    for model_name in models_to_try:
        try:
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
            except (TypeError, ValueError):
                model = genai.GenerativeModel(
                    model_name,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3,
                        max_output_tokens=_MAX_OUTPUT_TOKENS,
                    ),
                )
                inlined_prompt = f"SYSTEM INSTRUCTION & PEDAGOGICAL GUIDELINES:\n{system_inst}\n\nTEACHER QUESTION:\n{question}"
                response = model.generate_content(inlined_prompt)

            raw_text = (response.text or "").strip()
            text = clean_ai_output(raw_text)
            if text:
                return text
        except Exception as err:
            logger.warning("Gemini SDK model %s failed: %s", model_name, err)

    raise RuntimeError("All Gemini SDK models failed")


async def answer_question(question: str, section: str = "", module_title: str = "") -> str:
    """
    Answer a user's free-text question with module awareness and systematic guardrails.
    Never crashes, never leaves the teacher stranded.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set, using pedagogical knowledge engine")
        return answer_pedagogy_kb(question, section, module_title)

    # 1. Try SDK if available
    try:
        if genai is not None:
            return await asyncio.to_thread(_answer_sync, question, section, module_title)
    except Exception as sdk_err:
        logger.debug("Gemini SDK attempt failed: %s. Falling back to REST.", sdk_err)

    # 2. Try REST with dynamic discovery
    try:
        return await _answer_rest(question, section, module_title)
    except Exception as rest_err:
        logger.warning("Gemini REST attempt also failed: %s", rest_err)

    # 3. Guaranteed pedagogical knowledge-base engine fallback
    return answer_pedagogy_kb(question, section, module_title)


async def diagnose_gemini() -> dict:
    """Diagnostic tool to inspect API key and model discovery from admin dashboard."""
    api_key = _get_gemini_api_key()
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set in environment"}

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    info: dict = {
        "key_present": True,
        "key_preview": masked_key,
        "key_length": len(api_key),
        "v1beta_status": None,
        "v1_status": None,
        "available_models": [],
        "errors": [],
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check v1beta models
        try:
            r = await client.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}")
            info["v1beta_status"] = r.status_code
            if r.status_code == 200:
                models = [m.get("name", "") for m in r.json().get("models", [])]
                info["available_models"].extend(models)
            else:
                info["errors"].append(f"v1beta HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            info["errors"].append(f"v1beta error: {e}")

        # Check v1 models
        try:
            r_v1 = await client.get(f"https://generativelanguage.googleapis.com/v1/models?key={api_key}")
            info["v1_status"] = r_v1.status_code
            if r_v1.status_code == 200:
                models_v1 = [m.get("name", "") for m in r_v1.json().get("models", [])]
                for mv in models_v1:
                    if mv not in info["available_models"]:
                        info["available_models"].append(mv)
            else:
                info["errors"].append(f"v1 HTTP {r_v1.status_code}: {r_v1.text[:200]}")
        except Exception as e:
            info["errors"].append(f"v1 error: {e}")

    return info
