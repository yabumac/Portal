import os
import httpx
from fastapi import FastAPI, Request, Response

# --- CONFIGURATION ---
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

COURSES = [
    {"name": "Module 1 Classroom Management", "url": "https://app.mindsmith.ai/course/cmpba2car003a04jvn38qz6zd/learn"},
    {"name": "Module 2 Inclusive Quality Education", "url": "https://app.mindsmith.ai/course/cmph7l3ss001e0cjao5wox5kc/learn"},
    {"name": "Module 3 Adaptive & Learning Centered", "url": "https://app.mindsmith.ai/course/cmpbbbcf3004m04l7trxrvgh6/learn"},
    {"name": "Module 4 Digital Literacy", "url": "https://app.mindsmith.ai/course/cmpdnzj9d00yj04ih9efiqok7/learn"},
    {"name": "Module 5 Career Employability", "url": "https://app.mindsmith.ai/course/cmph6q0dh001c0bjlo1toswji/learn"},
    {"name": "Module 6 Educational Technology", "url": "https://app.mindsmith.ai/course/cmp5hsbon00tj04kziwu8xlmf/learn"},
]

app = FastAPI()

@app.get("/")
@app.get("/api/webhook")
async def verify_webhook(request: Request):
    """Handles Meta Webhook initial GET verification handshake"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)

@app.post("/")
@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """Handles incoming WhatsApp messages"""
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
                    
                    # Respond with the list of Mindsmith course links
                    await send_course_list(from_number)
    except Exception as e:
        print(f"Error parsing webhook payload: {e}")

    return {"status": "ok"}

async def send_course_list(to_number: str):
    """Sends formatted course links via WhatsApp Graph API"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    # WhatsApp supports rich text formatting (*bold*, _italics_) and link previews
    body_text = "👋 *Welcome! Select a course to begin:*\n\n"
    for course in COURSES:
        body_text += f"📘 *{course['name']}*\n🔗 {course['url']}\n\n"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": True,
            "body": body_text
        }
    }

    async with httpx.AsyncClient() as client:
        await client.post(url, headers=headers, json=payload)