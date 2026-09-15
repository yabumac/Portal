import os
import asyncio
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CONFIGURATION ---
# Use an environment variable for security!
BOT_TOKEN = os.getenv("BOT_TOKEN")

COURSES = [
    {"name": "Module 1 Classroom Management", "url": "https://app.mindsmith.ai/course/cmpba2car003a04jvn38qz6zd/learn"},
    {"name": "Module 2 Inclusive Quality Education", "url": "https://app.mindsmith.ai/course/cmph7l3ss001e0cjao5wox5kc/learn"},
    {"name": "Module 3 Adaptive & Learning Centered", "url": "https://app.mindsmith.ai/course/cmpbbbcf3004m04l7trxrvgh6/learn"},
    {"name": "Module 4 Digital Literacy", "url": "https://app.mindsmith.ai/course/cmpdnzj9d00yj04ih9efiqok7/learn"},
    {"name": "Module 5 Career Employability", "url": "https://app.mindsmith.ai/course/cmph6q0dh001c0bjlo1toswji/learn"},
    {"name": "Module 6 Educational Technology", "url": "https://app.mindsmith.ai/course/cmp5hsbon00tj04kziwu8xlmf/learn"},

]

app = FastAPI()

# Initialize the Telegram Application
# Note: We initialize it globally so it's reused across requests
ptb_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for course in COURSES:
        keyboard.append([InlineKeyboardButton(text=f"{course['name']}", web_app=WebAppInfo(url=course['url']))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Welcome! Select a course to begin:", reply_markup=reply_markup)

# Register handlers
ptb_app.add_handler(CommandHandler("start", start))

@app.post("/api/index.py")
@app.post("/api/webhook")
@app.post("/")
async def webhook_handler(request: Request):
    """Handles incoming updates from Telegram"""
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)

    async with ptb_app:
        await ptb_app.process_update(update)

    return {"status": "ok"}

@app.get("/")
def index():
    return {"message": "Mindsmith Bot is running!"}