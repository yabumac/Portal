import os
import httpx
from fastapi import FastAPI, Request, Response

# --- CONFIGURATION ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

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

app = FastAPI()

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
    
    if not mode:
        return {"status": "ok", "message": "Mindsmith WhatsApp Webhook is running!"}

    return Response(content="Verification failed", status_code=403)

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

                    # If user selected an item from the Interactive List Menu
                    if msg_type == "interactive":
                        interactive = incoming_msg.get("interactive", {})
                        if interactive.get("type") == "list_reply":
                            selected_id = interactive.get("list_reply", {}).get("id")
                            if selected_id in COURSES:
                                await send_cta_button(from_number, COURSES[selected_id])
                    else:
                        # Direct text input -> send Interactive List Menu
                        await send_interactive_list(from_number)
    except Exception as e:
        print(f"Error parsing webhook payload: {e}")

    return {"status": "ok"}

# --- HELPER: SEND INTERACTIVE LIST MENU ---
async def send_interactive_list(to_number: str):
    """Sends a native WhatsApp interactive menu drawer"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    rows = []
    for mod_id, course in COURSES.items():
        rows.append({
            "id": mod_id,
            "title": course["title"],
            "description": course["name"][:72]
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "Learning Hub"},
            "body": {"text": "Select a module below to begin your course:"},
            "footer": {"text": "EdTech Hub ET"},
            "action": {
                "button": "Select Module",
                "sections": [
                    {
                        "title": "Available Modules",
                        "rows": rows
                    }
                ]
            }
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)

# --- HELPER: SEND CTA URL BUTTON ---
async def send_cta_button(to_number: str, course: dict):
    """Sends a single card with a clean URL Action button"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "header": {"type": "text", "text": f"📘 {course['title']}: {course['name']}"},
            "body": {"text": "Tap the button below to launch the module:"},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": "🚀 Open Course",
                    "url": course["url"]
                }
            }
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)