import os
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse

# --- CONFIGURATION ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
# Vercel automatically sets VERCEL_URL; defaults to request host if not present
VERCEL_PROJECT_URL = os.getenv("VERCEL_URL", "")

COURSES = {
    "mod_1": {
        "title": "Module 1",
        "name": "Classroom Management",
        "url": "https://app.mindsmith.ai/course/cmpba2car003a04jvn38qz6zd/learn"
    },
    "mod_2": {
        "title": "Module 2",
        "name": "Inclusive Quality Education",
        "url": "https://app.mindsmith.ai/course/cmph7l3ss001e0cjao5wox5kc/learn"
    },
    "mod_3": {
        "title": "Module 3",
        "name": "Adaptive & Learning Centered",
        "url": "https://app.mindsmith.ai/course/cmpbbbcf3004m04l7trxrvgh6/learn"
    },
    "mod_4": {
        "title": "Module 4",
        "name": "Digital Literacy",
        "url": "https://app.mindsmith.ai/course/cmpdnzj9d00yj04ih9efiqok7/learn"
    },
    "mod_5": {
        "title": "Module 5",
        "name": "Career Employability",
        "url": "https://app.mindsmith.ai/course/cmph6q0dh001c0bjlo1toswji/learn"
    },
    "mod_6": {
        "title": "Module 6",
        "name": "Educational Technology",
        "url": "https://app.mindsmith.ai/course/cmp5hsbon00tj04kziwu8xlmf/learn"
    }
}

# 5-Step Diagnostic Questionnaire
QUESTIONS = [
    "Q1/5: Which primary language do you use most while teaching? (e.g., English, Amharic, Afaan Oromo)",
    "Q2/5: What main teaching materials do you have in class? (e.g., Textbooks, Digital devices, Blackboard only)",
    "Q3/5: What reading or skill level are most of your students at? (e.g., Beginners, Intermediate, Advanced)",
    "Q4/5: What is your primary classroom challenge right now? (e.g., Large class size, Engagement, Materials)",
    "Q5/5: How many years of teaching experience do you have? (e.g., 0-2 years, 3-5 years, 5+ years)"
]

# Simple in-memory session tracking for active user steps
USER_SESSIONS = {}

app = FastAPI()

# --- EMBEDDED HTML WRAPPER PLAYER ---
@app.get("/learn", response_class=HTMLResponse)
async def serve_course_player(mod: str = "mod_1"):
    """Serves the Mindsmith course cleanly inside an iframe without exposing the URL."""
    course_url = COURSES.get(mod, COURSES["mod_1"])["url"]
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>EdTech Hub - Online Course</title>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                background-color: #000000;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
        </style>
    </head>
    <body>
        <iframe src="{course_url}" allow="autoplay; fullscreen" allowfullscreen></iframe>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# --- WEBHOOK VERIFICATION (GET) ---
@app.get("/")
@app.get("/api")
@app.get("/api/webhook")
@app.get("/api/index.py")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    return {"status": "ok", "message": "WhatsApp Bot Engine Running"}

# --- INCOMING MESSAGES HANDLER (POST) ---
@app.post("/")
@app.post("/api")
@app.post("/api/webhook")
@app.post("/api/index.py")
async def webhook_handler(request: Request):
    data = await request.json()

    try:
        entries = data.get("entry", [])
        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                
                if messages:
                    incoming_msg = messages[0]
                    from_number = incoming_msg.get("from")
                    msg_type = incoming_msg.get("type")

                    # Handle List Reply Selection (Course Picked)
                    if msg_type == "interactive":
                        interactive = incoming_msg.get("interactive", {})
                        if interactive.get("type") == "list_reply":
                            selected_id = interactive.get("list_reply", {}).get("id")
                            if selected_id in COURSES:
                                # Start Questionnaire Flow
                                USER_SESSIONS[from_number] = {
                                    "selected_mod": selected_id,
                                    "step": 0
                                }
                                course_info = COURSES[selected_id]
                                intro_text = f"You selected *{course_info['title']}: {course_info['name']}*.\n\nTo tailor your experience, please answer 5 brief questions:\n\n{QUESTIONS[0]}"
                                await send_text_message(from_number, intro_text)
                                return {"status": "ok"}

                    # Handle Text Replies during Questionnaire Flow
                    if from_number in USER_SESSIONS:
                        session = USER_SESSIONS[from_number]
                        current_step = session["step"] + 1

                        if current_step < len(QUESTIONS):
                            # Move to next question
                            session["step"] = current_step
                            reply_text = f"Thank you.\n\n{QUESTIONS[current_step]}"
                            await send_text_message(from_number, reply_text)
                        else:
                            # Questionnaire Completed: Send Wrapper CTA Button
                            mod_id = session["selected_mod"]
                            course_data = COURSES[mod_id]
                            
                            # Construct local Vercel wrapper URL
                            host_url = VERCEL_PROJECT_URL
                            if not host_url.startswith("http"):
                                host_url = f"https://{host_url}" if host_url else str(request.base_url).rstrip('/')
                            
                            wrapper_url = f"{host_url}/learn?mod={mod_id}"
                            
                            del USER_SESSIONS[from_number] # Clear state
                            await send_completion_button(from_number, course_data, wrapper_url)
                    else:
                        # Direct menu presentation for new or reset conversations
                        await send_interactive_list(from_number)

    except Exception as e:
        print(f"Error handling webhook: {e}")

    return {"status": "ok"}

# --- HELPER FUNCTIONS ---
async def send_text_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def send_interactive_list(to_number: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    rows = [{"id": m_id, "title": m["title"], "description": m["name"][:72]} for m_id, m in COURSES.items()]
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Learning Hub"},
            "body": {"text": "Select a module to begin your questionnaire and course:"},
            "footer": {"text": "EdTech Hub ET"},
            "action": {
                "button": "Select Module",
                "sections": [{"title": "Available Modules", "rows": rows}]
            }
        }
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

async def send_completion_button(to_number: str, course: dict, wrapper_url: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "header": {"type": "text", "text": " Diagnostic Assessment Complete!"},
            "body": {"text": f"Thank you for completing the questions for *{course['title']}: {course['name']}*. Tap below to start learning:"},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": " Launch Course",
                    "url": wrapper_url
                }
            }
        }
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)