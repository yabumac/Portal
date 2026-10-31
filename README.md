# EdTech Hub - WhatsApp Learning Bot & Enterprise Admin Dashboard

> **Version 2.1** • Live Production Ready  
> AI-powered teacher-training companion bot delivered over WhatsApp, featuring complete student progress persistence, automatic course resumption, and an enterprise-grade real-time analytics console branded with the official EDTECH company logo.

---

## 🚀 Key Features & Capabilities

1. **Persistent Database Storage**:
   - Every learner is identified and saved by their **actual WhatsApp phone number** (`wa_id`, e.g. `+251911223344` or `+15551234567`).
   - Learner progress, completed modules, quiz answers, and self-assessment results are saved to persistent storage (`data/portal.db` SQLite by default, with auto-detection for PostgreSQL, Supabase, Neon, or Upstash Redis).
   - Removed the *"your progress has been reset (this server doesn't have a database yet)"* error permanently.
   - **Zero Sample Data**: Clean production database ready to record live teacher data as soon as they ping WhatsApp.

2. **Continue Where They Left Off Anytime**:
   - If a learner returns after hours, days, or weeks and sends `"hi"`, `"continue"`, or taps **"Resume Course"**, they are immediately picked up at their exact module and lesson.
   - Modules already finished are marked in `completed_lessons` so students never lose their completed work.
   - If a learner wants to start over, a dedicated **"Restart Course"** option is available.

3. **Enterprise SaaS Admin Intelligence Dashboard**:
   - Access at `/admin` or `/dashboard` (protected with `ADMIN_PASSWORD`, default: `admin123`).
   - **Branding**: Official circular **EDTECH** company logo integrated into the header, sign-in screen, and browser favicon.
   - **Real-Time Live Polling**: Automatic 30-second client-side polling and instant AJAX refresh without page reloads.
   - **Interactive Chart.js Visualizations**:
     - **Learner Status Donut Chart**: Live distribution of students across Course Completed, Learning Lessons, Quizzes, AI Tutor Mode, Self-Assessment, and Idle.
     - **Time-of-Day Habits Donut Chart**: Breakdown of when teachers study (Morning 06:00-12:00, Afternoon 12:00-17:00, Evening 17:00-22:00, Night 22:00-06:00).
     - **24-Hour Rhythm Area Chart**: Smooth curve showing exact hourly activity peaks across 24 hours UTC.
     - **11-Module Progression Funnel**: Bar chart displaying learner progression and drop-off across Modules 1 to 11.
   - **Educator AI Readiness Survey Analysis**: Aggregated breakdown of teacher AI usage frequency, confidence levels, primary challenges, and goals.
   - **Learners Directory**:
     - Real-time search filter by phone number and status filter tabs (All, Active, Graduated, AI Tutor, Idle).
     - Direct **"💬 WhatsApp"** button (`https://wa.me/...`) to open a direct chat with any student in 1 click.
     - **"Student Journey"** Modal: Interactive timeline displaying the complete chronological activity trail, quiz answers, and survey results.
     - **"Reset"** & **"Delete"** actions for learner lifecycle management.
   - **CSV Export**: Instant 1-click download of all actual learner records.

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
