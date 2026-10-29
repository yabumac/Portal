# EdTech Hub - WhatsApp Learning Bot & Admin Dashboard

An AI-powered teacher-training companion bot delivered over WhatsApp, featuring complete progress persistence, student resume capabilities, and a real-time admin analytics dashboard.

---

## 🚀 Key Improvements & Fixes

1. **Persistent Database Storage**:
   - Every learner is identified and saved by their **actual WhatsApp phone number** (`wa_id`, e.g. `+251911223344` or `+15551234567`).
   - Learner progress, completed modules, quiz answers, and self-assessment results are saved to persistent storage (`data/portal.db` SQLite by default, with auto-detection for cloud databases).
   - Removed the *"your progress has been reset (this server doesn't have a database yet)"* error permanently.

2. **Continue Where They Left Off Anytime**:
   - If a learner returns after hours, days, or weeks and sends `"hi"`, `"continue"`, or taps **"Resume Course"**, they are immediately picked up at their exact module and lesson.
   - Modules already finished are marked in `completed_lessons` so students never lose their completed work.
   - If a learner wants to start over, a dedicated **"Restart Course"** option is available.

3. **Admin Analytics Dashboard**:
   - Access at `/admin` or `/dashboard` (protected with `ADMIN_PASSWORD`, default: `admin123`).
   - **Overview Metrics**: Total learners, active learners, course completions, self-assessment responses, and total interactions.
   - **"When Are They Learning?"**:
     - Visual 24-hour activity distribution chart (00:00 - 23:00 UTC) revealing peak learning hours.
     - Time-of-day categories: Morning (06:00 - 12:00), Afternoon (12:00 - 17:00), Evening (17:00 - 22:00), Night (22:00 - 06:00).
     - Daily volume by day of the week (Monday - Sunday).
   - **11-Module Progression Funnel**: See how many learners reached and completed Modules 1 through 11.
   - **Teacher AI Readiness Survey Insights**: Aggregated breakdown of teacher AI usage, confidence levels, challenges, and course goals.
   - **Learners Directory**:
     - Live search by phone number.
     - Progress bars (% complete) and status badges (In Progress, Quiz, AI Tutor, Completed).
     - Direct WhatsApp link to chat with the student with 1 click.
     - **Learner Journey Modal**: Full chronological timeline of every event logged for that student.
     - **Reset Progress Action**: Reset an individual student if needed.
     - **Export to CSV**: Download user and activity data for Excel / Google Sheets.

---

## 🛠️ Running Locally

### 1. Start the FastAPI Server:
```bash
uvicorn api.index:app --reload --port 8000
```

- **Admin Dashboard**: Open [http://localhost:8000/admin](http://localhost:8000/admin) in your browser.
  - Password: `admin123` (or whatever `ADMIN_PASSWORD` is set to).
- **Health Check**: [http://localhost:8000/](http://localhost:8000/)

### 2. Interactive Terminal Playground (Test without Meta credentials):
```bash
python scripts/chat.py
```
Type `hi`, `enroll`, `continue`, `A`, `B`, `C`, or ask any question to test the AI Tutor locally.

---

## 🗄️ Database Configuration

The application uses an adaptive database architecture (`bot/db.py`):

| Backend | Environment Variables | Notes |
| :--- | :--- | :--- |
| **SQLite (Default)** | `DATABASE_PATH` or `SQLITE_PATH` | Zero setup! Automatically stored in `data/portal.db` (or `/tmp/portal.db` in serverless). |
| **PostgreSQL / Neon / Supabase** | `DATABASE_URL` or `POSTGRES_URL` | Set your connection string in Vercel / Railway / Render. |
| **Upstash Redis / Vercel KV** | `UPSTASH_REDIS_REST_URL` & `UPSTASH_REDIS_REST_TOKEN` | 100% serverless over HTTP via `httpx` (no drivers required). Ideal for Vercel! |

---

## 🔐 Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ADMIN_PASSWORD` | Password for `/admin` dashboard | `admin123` |
| `VERIFY_TOKEN` | Meta WhatsApp Webhook verification token | `local-test` |
| `WHATSAPP_TOKEN` | Meta Graph API permanent access token | None |
| `PHONE_NUMBER_ID` | Meta WhatsApp Cloud API Phone Number ID | None |
| `GEMINI_API_KEY` | Google Gemini API Key for AI Tutor | None |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `MOCK_SEND` | Set to `1` or `true` for local testing without Meta | `false` |
