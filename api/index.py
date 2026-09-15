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

# --- WEBHOOK VERIFICATION (GET) ---
@app.get("/")
@app.get("/api")
@app.get("/api/webhook")
@app.get("/api/index.py")
async def verify_webhook(request: Request):
    """Handles Meta Webhook GET verification handshake and browser status checks"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    # Handshake request coming from Meta
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    # Direct browser visit check
    if not mode:
        return {"status": "ok", "message": "Mindsmith WhatsApp Webhook is running!"}

    return Response(content="Verification failed", status_code=403)

# --- INCOMING MESSAGES HANDLER (POST) ---
@app.post("/")
@app.post("/api")
@app.post("/api/webhook")
@app.post("/api/index.py")
async def webhook_handler(request: Request):
    """Handles incoming WhatsApp messages from Meta"""
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

# --- HELPER FUNCTION TO SEND MESSAGES VIA META API ---
async def send_course_list(to_number: str):
    """Sends formatted course links via WhatsApp Graph API"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

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