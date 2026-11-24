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

DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-pro",
]

_MAX_ANSWER_WORDS = 130
_MAX_OUTPUT_TOKENS = 500

# Cache discovered models for 10 minutes
_DISCOVERED_MODELS_CACHE: list[str] = []
_DISCOVERED_CACHE_TIME: float = 0.0


def _get_gemini_api_key() -> Optional[str]:
    """Retrieve Gemini API key from environment, stripped of quotes or whitespace."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return key.strip().strip('"').strip("'")
    return None


def _build_system_instruction(section: str = "", module_title: str = "") -> str:
    current_module_label = module_title.strip() if module_title else "Introduction to AI for Teachers in Ethiopia"
    clean_context = section.strip() if section else "General Course Curriculum"

    # Simplified, friendly AI tutor prompt without restrictive guardrails
    return f"""You are a helpful and friendly AI Tutor for Ethiopian primary and secondary school teachers taking the course: "Introduction to Artificial Intelligence (AI) for Teachers in Ethiopia".

Context:
- Current Module: {current_module_label}
- Lesson Context: {clean_context}

Guidelines:
- Answer the teacher's question directly, clearly, and conversationally.
- Be warm, encouraging, practical, and helpful.
- Keep your answers concise, easy to understand, and formatted cleanly for mobile reading on WhatsApp.
"""

    # --- Previous strict guardrails commented out as requested ---
    # CRITICAL RESPONSE FORMAT RULES:
    # 1. Output ONLY your direct conversational message to the teacher.
    # 2. Structure your reply in exactly three parts:
    #    - Part 1: Exactly ONE concise introductory paragraph (2-3 sentences) directly explaining the core concept.
    #    - Part 2: Exactly 2 or 3 bullet points (* ) providing practical, low-resource classroom strategies for Ethiopian schools
    #    - Part 3: Exactly ONE short, encouraging concluding sentence.
    # OFF-TOPIC GUARDRAIL:
    # If the user asks questions completely unrelated to education or teaching:
    # Politely reply: "I am your AI Tutor dedicated to the 'AI for Teaching and Learning' course..."


# ---------------------------------------------------------------------------
# Solid Pedagogical Knowledge-Base Engine (Guaranteed Fallback & Workaround)
# ---------------------------------------------------------------------------

MODULE_CURATED_EXPLANATIONS = {
    1: (
        "In Module 1, we learn about Understanding Artificial Intelligence (AI). "
        "AI is a technology that enables computers and machines to perform tasks that normally require "
        "human intelligence, such as learning from information, recognizing patterns, understanding language, "
        "and generating content.\n\n"
        "AI is already part of our daily lives through voice recognition on phones, Google Maps navigation, "
        "language translation tools, face recognition, and tools like ChatGPT. In education, AI helps teachers "
        "prepare lesson plans, create materials, and generate assessments, while supporting personalized learning for students.\n\n"
        "Remember, AI is a tool to support your work—not to replace your creativity and professional judgment as an educator!"
    ),
    2: (
        "In Module 2, we introduce the 5-Part Teacher Prompt Formula to transform generic AI responses into highly practical classroom resources. "
        "Providing explicit structure prevents the AI from suggesting unrealistic activities or expensive digital tools.\n\n"
        "* Core 5 Parts: Always specify Role (Grade 7 Science teacher), Context (55 students in Ethiopia), Task (15-minute group activity), Constraints (chalkboard only, local materials), and Output Format (numbered steps).\n"
        "* Set Clear Boundaries: Specifying your exact class size and device limitations forces the AI to output practical, low-resource ideas.\n"
        "* Reusable Templates: Save your best 5-part prompt structures on your phone to quickly draft future weekly lessons.\n\n"
        "Clear teacher prompts produce relevant, classroom-ready materials."
    ),
    3: (
        "In Module 3, we focus on practical teaching in low-connectivity, large-enrollment classrooms (50+ students). "
        "You never need classroom internet or student devices—you apply the 'Batch Preparation' methodology.\n\n"
        "* Batch Preparation: Use a single phone with internet at home or school to generate weekly quizzes, reading texts, and bilingual glossaries in advance.\n"
        "* Chalkboard Delivery: Transcribe generated exercises, discussion prompts, or diagrams directly onto the blackboard for the whole class.\n"
        "* Collaborative Stations: Organize small peer groups of 5-8 students sharing a single written prompt or task sheet.\n\n"
        "Resource constraints never limit great teaching when you prepare strategically."
    ),
    4: (
        "In Module 4, we walk through the 5-Step Lesson Planning Workflow designed for standard 40-45 minute periods. "
        "AI serves as your rapid ideation assistant to create engaging, curriculum-aligned lesson structures.\n\n"
        "* Hook & Objective: Prompt AI for a 5-minute curiosity-sparking local riddle or story to start the period with high energy.\n"
        "* Direct & Guided Instruction: Use AI to draft tiered explanations, everyday analogies, and paired student practice tasks.\n"
        "* Exit Ticket: Conclude the period with 2 diagnostic exit questions to check whether students achieved the core competency.\n\n"
        "AI speeds up lesson planning so you can dedicate more energy to your students."
    ),
    5: (
        "In Module 5, we explore Formative Assessment and the 'Evidence to Action' cycle. "
        "Rather than focusing on grading, formative assessment provides real-time evidence of student understanding so you can adjust your teaching immediately.\n\n"
        "* Diagnostic Questions: Ask AI to create multiple-choice exit tickets with plausible distractors that expose common misconceptions.\n"
        "* Rapid Classroom Checks: Use thumbs-up/down signals, slate boards, or finger counts to quickly assess 50+ students at once.\n"
        "* Targeted Re-Teaching: Prompt AI for alternative visual analogies or hands-on activities to re-explain topics that students found difficult.\n\n"
        "Assessment becomes an ongoing compass to guide classroom learning."
    ),
    6: (
        "In Module 6, we examine Universal Design for Learning (UDL) to support mixed-ability classrooms and diverse learners. "
        "AI allows you to quickly differentiate instruction so every student can access the same core curriculum.\n\n"
        "* Tiered Texts: Use AI to take a core reading passage and instantly generate simplified, standard, and enriched reading versions.\n"
        "* Multiple Representations: Generate bilingual word banks (English and Amharic) and visual descriptions for complex vocabulary.\n"
        "* Flexible Demonstration: Allow learners to show mastery through oral presentations, drawings, or chalkboard demonstrations.\n\n"
        "Inclusion provides diverse pathways for every student to succeed."
    ),
    7: (
        "In Module 7, we address Responsible AI, student data privacy, and ethical classroom stewardship. "
        "Teachers play a vital role in ensuring AI is used safely, securely, and with cultural integrity.\n\n"
        "* Data Privacy: Never enter student names, identification numbers, grades, or personal details into any AI system.\n"
        "* Cultural Relevance: Review every generated example to verify it aligns with Ethiopian culture, geography, and values.\n"
        "* Professional Leadership: Share your verified prompt templates and lesson plans with fellow teachers in your school.\n\n"
        "Your ethical guidance ensures technology serves safe and meaningful educational progress."
    ),
}


def get_module_number(module_title: str, section: str = "") -> int:
    """Identify the 1-indexed module number from module title or section context."""
    text = f"{module_title} {section}".lower()
    for i in range(1, 8):
        if f"module {i}" in text or f"lesson_{i}" in text or f"lesson {i}" in text:
            return i
    if "basics" in text or "editor" in text:
        return 1
    if "prompt" in text or "formula" in text:
        return 2
    if "offline" in text or "low-resource" in text or "ethiopian classroom" in text:
        return 3
    if "lesson planning" in text or "5-step" in text:
        return 4
    if "assessment" in text or "formative" in text or "evidence" in text:
        return 5
    if "udl" in text or "inclusive" in text or "differentiat" in text:
        return 6
    if "responsible" in text or "privacy" in text or "ethics" in text or "action plan" in text:
        return 7
    return 1


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
    Guarantees an accurate, structured answer: 1 intro paragraph + 3 bullet points + 1 closing sentence.
    """
    low_q = question.lower().strip()
    active_module = module_title.strip() if module_title else "AI for Teaching and Learning"
    mod_num = get_module_number(active_module, section)

    # Guardrail check
    if _is_off_topic(low_q):
        return (
            f"I am your AI Tutor dedicated specifically to the 'AI for Teaching and Learning' course. "
            f"I can only assist with pedagogical strategies and your current module ({active_module}). "
            f"Feel free to ask any question about this lesson or how to use AI in your classroom!"
        )

    # Topic 1: Teacher as Editor / Controller / Review
    if any(k in low_q for k in ("controller", "control", "editor", "authority", "hallucinat", "fact check", "trust", "review")):
        return (
            f"In {active_module}, the central principle is 'The Teacher as Editor and Controller.' "
            "Generative AI does not possess pedagogical judgment or factual consciousness—it is a statistical prediction engine. "
            "Therefore, the educator must always review and adapt AI suggestions before using them in class.\n\n"
            "* Align with Standards: Review every AI draft against your national curriculum standards to verify localized accuracy.\n"
            "* Verify Facts & Context: Check all facts, numbers, and cultural references to ensure they fit Ethiopian classrooms.\n"
            "* Differentiate for Learners: Adjust vocabulary and difficulty to match the actual reading levels of your students.\n\n"
            "AI serves as your preparation assistant, but you maintain full pedagogical authority."
        )

    # Topic 2: 5-Part Formula / Prompting
    if any(k in low_q for k in ("prompt", "formula", "5-part", "5 part", "how to prompt", "instruction", "output format")):
        return (
            "The 5-Part Prompt Formula ensures AI generates relevant, practical classroom materials rather than generic textbook summaries. "
            "By setting clear boundaries upfront, you save planning time and avoid unrealistic suggestions.\n\n"
            "* Role & Context: State who the AI is acting as (e.g. Grade 8 General Science teacher) and your classroom setting (e.g. 55 students in Ethiopia).\n"
            "* Task & Constraints: Define what to create (e.g. 15-minute paired task) with clear constraints (chalkboard only, no student devices).\n"
            "* Output Format: Request a structured delivery format, such as numbered instructions, discussion questions, or a short glossary.\n\n"
            "Including all 5 elements turns generic responses into classroom-ready materials."
        )

    # Topic 3: Low-Resource & Offline Preparation / Single Device / Large Classes
    if any(k in low_q for k in ("offline", "low resource", "internet", "connectivity", "phone", "chalkboard", "blackboard", "large class", "50")):
        return (
            "In schools with low internet connectivity or large classes (50+ students), apply the 'Batch Preparation' methodology. "
            "You do not need internet or computers in the classroom—you use a single phone during connectivity hours to plan ahead.\n\n"
            "* Batch Preparation: Generate lesson plans, tiered reading passages, and diagnostic exit tickets at home or where internet is available.\n"
            "* Chalkboard Delivery: Transcribe generated exercises, discussion prompts, and diagrams onto the blackboard for the whole class.\n"
            "* Peer Group Work: Have small teams of 5-8 students share a single written prompt or activity sheet to foster collaborative learning.\n\n"
            "Strategic preparation allows you to deliver modern, engaging pedagogy completely offline."
        )

    # Topic 4: Lesson Planning / 5-Step Structure
    if any(k in low_q for k in ("lesson plan", "planning", "5-step", "5 step", "objective", "hook", "guided practice")):
        return (
            "The 5-Step Lesson Planning Workflow structures a standard 40-45 minute period into an engaging, competency-based learning experience. "
            "AI acts as a fast ideation partner to draft each stage of the instructional period.\n\n"
            "* Hook & Objective: Prompt AI for a 5-minute curiosity-sparking local riddle or story to start the period with high energy.\n"
            "* Direct & Guided Instruction: Use AI to draft tiered explanations, everyday analogies, and paired student practice tasks.\n"
            "* Exit Ticket: Conclude the period with 2 diagnostic exit questions to check whether students achieved the core competency.\n\n"
            "AI speeds up lesson preparation so you can focus your attention on student engagement."
        )

    # Topic 5: Formative Assessment / Evidence to Action / Exit Tickets
    if any(k in low_q for k in ("assessment", "formative", "quiz", "evidence", "ticket", "exit", "diagnos", "re-teach")):
        return (
            "Formative assessment is about transforming 'Evidence into Action' during the lesson rather than grading students. "
            "It gives you real-time feedback on what students understand so you can adjust your instruction immediately.\n\n"
            "* Plausible Distractors: Prompt AI to create multiple-choice exit tickets where wrong answers reveal specific common misunderstandings.\n"
            "* Rapid Evidence Collection: Use quick gestures (thumbs-up/down) or slate boards to rapidly assess understanding across 50+ students.\n"
            "* Targeted Re-Teaching: Ask AI for an alternative visual metaphor or hands-on activity to re-teach confusing concepts the next day.\n\n"
            "The purpose of formative assessment is continuous learning adjustment, not assigning punitive scores."
        )

    # Topic 6: Universal Design for Learning (UDL) / Inclusion / Differentiation
    if any(k in low_q for k in ("udl", "universal design", "differentiat", "inclusion", "struggl", "advanced", "tier", "special")):
        return (
            "Universal Design for Learning (UDL) ensures every student in a diverse, mixed-ability classroom can access the curriculum. "
            "AI allows you to quickly differentiate materials so all learners achieve the same core competencies.\n\n"
            "* Tiered Texts: Prompt AI to take a core reading passage and instantly create simplified, standard, and enriched reading levels.\n"
            "* Multiple Representations: Generate bilingual word banks (English and Amharic) and visual descriptions for complex concepts.\n"
            "* Flexible Demonstration: Allow students to express their learning through oral presentations, drawings, or chalkboard demonstrations.\n\n"
            "Inclusion provides diverse pathways for every student to succeed."
        )

    # Topic 7: Privacy, Safety, Ethics, and Bias
    if any(k in low_q for k in ("privacy", "safety", "ethic", "bias", "pii", "student name", "data", "protect")):
        return (
            "Student data protection and ethical AI use are foundational responsibilities for modern educators. "
            "You must ensure AI is used safely, securely, and with cultural integrity in your school.\n\n"
            "* Never Share PII: Never enter student names, identification numbers, grades, or personal family details into any AI system.\n"
            "* Use Generic Personas: Describe learner needs generically instead (e.g., 'A Grade 6 student struggling with multi-step word problems').\n"
            "* Inspect Cultural Relevance: Review every generated example to verify it aligns with Ethiopian culture, geography, and values.\n\n"
            "Your professional leadership ensures AI serves safe and meaningful educational progress."
        )

    # Default: Return curated 1-paragraph + 3-bullet-point response for active module
    return MODULE_CURATED_EXPLANATIONS.get(mod_num, MODULE_CURATED_EXPLANATIONS[1])


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


META_PATTERNS = [
    r"ethiopian educator taking",
    r"module \d+:\s*ai basics",
    r"friendly,\s*encouraging,\s*warm",
    r"under \d+\s*words",
    r"plain text",
    r"no meta-talk",
    r"no bulleted checklists",
    r"prompt says",
    r"the prompt",
    r"referring to the current",
    r"i'll stick to",
    r"i will stick to",
    r"let's stick to",
    r"^\s*\*\s*(greeting|explanation|goal|domain|constraints?|concept|draft|drafting|formatting|tone|word count|user question|current module|role|context|content check|constraint check|ai basics|categories|core principle|example)\b",
    r"^\s*(greeting|explanation|goal|domain|constraints?|draft|drafting|formatting|tone|word count):",
    r"\b(draft\s*\d*|final response)\s*:",
    r"^\s*\*\s+[a-z\s]+:\s*[a-z\s]+\([^\)]+\)",
]


def clean_ai_output(t: str, fallback_fn=None) -> str:
    """
    Sanitize model output:
    1. Strips <thought>...</thought> tags if present.
    2. Strips Markdown headers.
    """
    if not t:
        return fallback_fn() if fallback_fn else ""
    t = t.strip()

    # Strip XML thinking or reasoning tags
    t = re.sub(r"<thought>.*?</thought>", "", t, flags=re.DOTALL).strip()
    t = re.sub(r"<reasoning>.*?</reasoning>", "", t, flags=re.DOTALL).strip()
    t = re.sub(r"\[thought\].*?\[/thought\]", "", t, flags=re.DOTALL | re.IGNORECASE).strip()

    # Strip markdown headers (##, ###, etc.)
    t = re.sub(r"^\s*#{1,6}\s*", "", t, flags=re.MULTILINE).strip()

    return t

    # --- Previous heavy meta-pattern filtering commented out as requested ---
    # has_meta = any(re.search(pat, t, re.MULTILINE | re.IGNORECASE) for pat in META_PATTERNS)
    # if has_meta:
    #     draft_match = re.search(r'(?:Draft\s*\d*|Drafting|Final Response):\s*(.*?)(?=\n\s*\*|\Z)', t, flags=re.DOTALL | re.IGNORECASE)
    #     if draft_match:
    #         candidate = draft_match.group(1).strip().strip('"')
    #         if len(candidate) > 60 and not any(re.search(pat, candidate, re.IGNORECASE) for pat in META_PATTERNS):
    #             return candidate
    #     return fallback_fn() if fallback_fn else ""


async def _call_gemini_fast(question: str, section: str, module_title: str) -> Optional[str]:
    """
    Direct, lightweight async REST call to Gemini with tight per-request timeouts.
    Never blocks threads, never performs slow discovery.
    """
    api_key = _get_gemini_api_key()
    if not api_key:
        return None

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
            "maxOutputTokens": 320,
        }
    }

    payload_clean_inlined = {
        "contents": [
            {
                "role": "user",
                "parts": [{
                    "text": (
                        f"You are a helpful WhatsApp AI tutor for Ethiopian educators on {module_title}.\n"
                        f"Teacher's question: {question}\n\n"
                        "Please answer directly in exactly 1 short paragraph plus 2-3 bullet points (* ) for practical classroom application."
                    )
                }]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 320,
        }
    }

    candidate_models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
    preferred = os.getenv("GEMINI_MODEL")
    if preferred and preferred not in candidate_models:
        candidate_models.insert(0, preferred)

    # 3.8s HTTP timeout per request
    async with httpx.AsyncClient(timeout=3.8) as client:
        for model_name in candidate_models[:2]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            for payload in (payload_primary, payload_clean_inlined):
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            valid_parts = [
                                p.get("text", "").strip()
                                for p in parts
                                if p.get("text") and not p.get("thought", False)
                            ]
                            raw_text = "\n".join(valid_parts).strip() if valid_parts else (parts[-1].get("text", "").strip() if parts else "")
                            cleaned = clean_ai_output(raw_text, fallback_fn=None)
                            if cleaned:
                                return cleaned
                    else:
                        logger.debug("Fast REST %s HTTP %s: %s", model_name, resp.status_code, resp.text[:100])
                except Exception as req_err:
                    logger.debug("Fast REST %s error: %s", model_name, req_err)
                    break

    return None


async def answer_question(question: str, section: str = "", module_title: str = "") -> str:
    """
    Answer a user's free-text question with module awareness and systematic guardrails.
    Guaranteed to return in <= 4.5 seconds. Never hangs, never crashes, never leaves
    the teacher stranded.
    """
    api_key = _get_gemini_api_key()
    if api_key:
        try:
            # Enforce 4.5s hard ceiling so Vercel & WhatsApp never time out
            result = await asyncio.wait_for(
                _call_gemini_fast(question, section, module_title),
                timeout=4.5
            )
            if result:
                return result
        except asyncio.TimeoutError:
            logger.warning("Gemini API exceeded 4.5s; immediately delivering curated pedagogical KB")
        except Exception as e:
            logger.warning("Gemini call exception: %s", e)

    # Seamless instant pedagogical knowledge base fallback (0.001s)
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
