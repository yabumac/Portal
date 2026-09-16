# import os
# import logging
# import httpx
# from fastapi import FastAPI, Request, Response
# from fastapi.responses import HTMLResponse

# # Configure logging to see output in Vercel Logs
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("whatsapp_bot")

# # --- CONFIGURATION ---
# WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
# PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
# VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# COURSES = {
#     "mod_1": {
#         "title": "Module 1",
#         "name": "Classroom Management",
#         "url": "https://app.mindsmith.ai/course/cmpba2car003a04jvn38qz6zd/learn"
#     },
#     "mod_2": {
#         "title": "Module 2",
#         "name": "Inclusive Quality Education",
#         "url": "https://app.mindsmith.ai/course/cmph7l3ss001e0cjao5wox5kc/learn"
#     },
#     "mod_3": {
#         "title": "Module 3",
#         "name": "Adaptive & Learning Centered",
#         "url": "https://app.mindsmith.ai/course/cmpbbbcf3004m04l7trxrvgh6/learn"
#     },
#     "mod_4": {
#         "title": "Module 4",
#         "name": "Digital Literacy",
#         "url": "https://app.mindsmith.ai/course/cmpdnzj9d00yj04ih9efiqok7/learn"
#     },
#     "mod_5": {
#         "title": "Module 5",
#         "name": "Career Employability",
#         "url": "https://app.mindsmith.ai/course/cmph6q0dh001c0bjlo1toswji/learn"
#     },
#     "mod_6": {
#         "title": "Module 6",
#         "name": "Educational Technology",
#         "url": "https://app.mindsmith.ai/course/cmp5hsbon00tj04kziwu8xlmf/learn"
#     }
# }

# QUESTIONS = [
#     "Q1/5: Which language do you primarily use in your classroom? (e.g., English, Amharic, Afaan Oromo)",
#     "Q2/5: What main teaching materials do you have available? (e.g., Textbooks, Digital devices, Blackboard only)",
#     "Q3/5: What reading or skill level are most of your students at? (e.g., Beginners, Intermediate, Advanced)",
#     "Q4/5: What is your primary classroom challenge right now? (e.g., Large class size, Engagement, Lack of materials)",
#     "Q5/5: How many years of teaching experience do you have? (e.g., 0-2 years, 3-5 years, 5+ years)"
# ]

# USER_SESSIONS = {}

# app = FastAPI()

# def render_iframe_wrapper(course_url: str) -> str:
#     return f"""<!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
#     <title>EdTech Hub Learning Portal</title>
#     <style>
#         * {{ margin: 0; padding: 0; box-sizing: border-box; }}
#         html, body {{
#             width: 100%;
#             height: 100%;
#             height: 100dvh;
#             overflow: hidden;
#             background-color: #0f172a;
#             font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
#         }}
#         iframe {{
#             width: 100%;
#             height: 100%;
#             height: 100dvh;
#             border: 0;
#             display: block;
#         }}
#     </style>
# </head>
# <body>
#     <iframe src="{course_url}" allow="autoplay; fullscreen; microphone; camera; display-capture" allowfullscreen></iframe>
# </body>
# </html>"""

# # --- CATCH-ALL GET HANDLER ---
# @app.get("/{path:path}")
# async def handle_get(request: Request, path: str = ""):
#     params = request.query_params

#     # Check if this is a request to open a course module
#     if "mod" in params or "learn" in path:
#         mod_id = params.get("mod", "mod_1")
#         course_data = COURSES.get(mod_id, COURSES["mod_1"])
#         return HTMLResponse(content=render_iframe_wrapper(course_data["url"]))

#     # Webhook Verification
#     mode = params.get("hub.mode")
#     token = params.get("hub.verify_token")
#     challenge = params.get("hub.challenge")

#     if mode == "subscribe" and token == VERIFY_TOKEN:
#         return Response(content=challenge, media_type="text/plain")

#     return Response(content='{"status": "ok", "message": "WhatsApp Bot Engine Running"}', media_type="application/json")

# # --- CATCH-ALL POST HANDLER ---
# @app.post("/{path:path}")
# async def handle_post(request: Request, path: str = ""):
#     try:
#         data = await request.json()
#         entries = data.get("entry", [])
        
#         for entry in entries:
#             for change in entry.get("changes", []):
#                 value = change.get("value", {})
#                 messages = value.get("messages", [])
                
#                 if messages:
#                     incoming_msg = messages[0]
#                     from_number = incoming_msg.get("from")
#                     msg_type = incoming_msg.get("type")

#                     # Handle Module Selection from Menu
#                     if msg_type == "interactive":
#                         interactive = incoming_msg.get("interactive", {})
#                         if interactive.get("type") == "list_reply":
#                             selected_id = interactive.get("list_reply", {}).get("id")
#                             if selected_id in COURSES:
#                                 course_data = COURSES[selected_id]
#                                 host = request.headers.get("host") or os.getenv("VERCEL_URL", "")
#                                 if host and not host.startswith("http"):
#                                     host = f"https://{host}"
                                
#                                 wrapper_url = f"{host}/api?mod={selected_id}"
#                                 await send_completion_button(from_number, course_data, wrapper_url)
#                                 return {"status": "ok"}

#                     # Handle User Responses during Questionnaire Flow
#                     if from_number in USER_SESSIONS:
#                         session = USER_SESSIONS[from_number]
#                         current_step = session["step"] + 1

#                         if current_step < len(QUESTIONS):
#                             session["step"] = current_step
#                             await send_text_message(from_number, f"Thank you.\n\n{QUESTIONS[current_step]}")
#                         else:
#                             del USER_SESSIONS[from_number]
#                             await send_interactive_list(from_number)
#                     else:
#                         # Initial Start / Greeting
#                         USER_SESSIONS[from_number] = {"step": 0}
#                         intro_text = f"Welcome! Before we begin, please answer 5 brief questions to help us tailor your experience:\n\n{QUESTIONS[0]}"
#                         await send_text_message(from_number, intro_text)

#     except Exception as e:
#         logger.error(f"Error handling webhook POST: {e}", exc_info=True)

#     return {"status": "ok"}

# # --- HELPER FUNCTIONS WITH LOGGING ---
# async def send_text_message(to_number: str, text: str):
#     url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to_number,
#         "type": "text",
#         "text": {"body": text}
#     }
#     async with httpx.AsyncClient() as client:
#         res = await client.post(url, headers=headers, json=payload)
#         logger.info(f"Send Text Status: {res.status_code} - Response: {res.text}")

# async def send_interactive_list(to_number: str):
#     url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
#     rows = [{"id": m_id, "title": m["title"], "description": m["name"][:72]} for m_id, m in COURSES.items()]
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to_number,
#         "type": "interactive",
#         "interactive": {
#             "type": "list",
#             "header": {"type": "text", "text": "🎉 Diagnostic Complete!"},
#             "body": {"text": "Thank you for completing the assessment! Select a course module below to begin learning:"},
#             "footer": {"text": "EdTech Hub ET"},
#             "action": {
#                 "button": "Select Module",
#                 "sections": [{"title": "Available Modules", "rows": rows}]
#             }
#         }
#     }
#     async with httpx.AsyncClient() as client:
#         res = await client.post(url, headers=headers, json=payload)
#         logger.info(f"Send List Status: {res.status_code} - Response: {res.text}")

# async def send_completion_button(to_number: str, course: dict, wrapper_url: str):
#     url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
#     headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to_number,
#         "type": "interactive",
#         "interactive": {
#             "type": "cta_url",
#             "header": {"type": "text", "text": f"📘 {course['title']}: {course['name']}"},
#             "body": {"text": "Tap the button below to launch the module:"},
#             "action": {
#                 "name": "cta_url",
#                 "parameters": {
#                     "display_text": "🚀 Launch Course",
#                     "url": wrapper_url
#                 }
#             }
#         }
#     }
#     async with httpx.AsyncClient() as client:
#         res = await client.post(url, headers=headers, json=payload)
#         logger.info(f"Send CTA Status: {res.status_code} - Response: {res.text}")