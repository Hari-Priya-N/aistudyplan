# Pathwise — Personalized Learning Path Generator
## High-level code documentation

This document explains what the application does, how it is organised, the
purpose of every file, and the exact steps to run it locally and online.

---

## 1. What the application does

Pathwise is an AI-powered adaptive tutor for schools and colleges. Faculty
upload course content into subjects; the system extracts a topic graph from
it; each student gets a personalised study path for the subjects (core +
electives) they are enrolled in. Students self-assess with a **pre-assessment**,
study with AI-generated **study kits**, re-test, and get **remediation** when
they fall below mastery. **Elara**, the AI tutor chat, answers questions
grounded in the uploaded material. Management sees improvement metrics across
the whole institution.

### Three user views

| View | Who | What they can do |
|---|---|---|
| **Student** | learners | Study path per subject, pre-assessment → study kit → post-preparation test → practice tests, Elara chat (daily quota), *My progress* (logins, sessions, scores, improvement), *Rewards* (points, level, badges, streak, class leaderboard). Upload is visible but greyed out. |
| **Faculty** | teachers | Add/upload content (file or typed notes) into their subjects, register students from an Excel sheet (with subjects + electives), dashboard with **limited** per-student metrics for their own subjects, drill-down per student. |
| **Management** | principal / HoD | Predominantly a metric dashboard: overview, class, subject, elective, faculty and student level; pre-assessment, post-preparation and consecutive scores; improvement and focus areas per student; CSV export; assign faculty to subjects. |

### Mentor review comments → where they are implemented

| Review comment | Implementation |
|---|---|
| High-level code docs: purpose of each file + run steps | This document (§4 file guide, §5–6 run/deploy) |
| Faculty: add and upload content | `pages/Upload.jsx` (file upload **or** typed notes, per subject) → `routers/syllabus.py` |
| Faculty: dashboard with limited metrics per student | `pages/FacultyDashboard.jsx` → `routers/faculty.py` (`limited=True` in `services/analytics.py`: only their subjects, no points/time detail) |
| Faculty: upload student list (email + roll/admission no) via Excel, with subjects so electives are handled | `pages/Roster.jsx` → `routers/roster.py` → `services/roster.py` (template download, `.xlsx`/`.csv`, Subjects + Electives columns → `Enrollment` rows) |
| Management: metric dashboard at class, subject, student, faculty, elective level | `pages/ManagementDashboard.jsx` (tabs) → `routers/analytics.py` → `services/analytics.py` |
| Management: pre-assessment, post-preparation and consecutive scores | `QuizAttempt.kind` (`pre_assessment` / `post_preparation` / `practice`); "score journey" in `services/analytics.py` |
| Focus on improvement and focus areas of each student | `improvement = latest − pre-assessment`; focus areas = topics below 75 %, weakest first — shown at every level |
| Student: track logins, sessions, scores, improvement — visible to the student | `UserSession` + `ActivityEvent` models, heartbeat in `context/AuthContext.jsx`, student page `pages/Progress.jsx` |
| Student: limit uploads — show but grey out | `ALLOW_STUDENT_UPLOADS=false` (default): backend returns 403, `Upload.jsx` renders a greyed, disabled page with a 🔒 in the nav |
| Motivate students to self-assess; incentivise with credits / bonus points | `services/gamification.py` + `pages/Rewards.jsx` (see §7) |
| Limit Elara chat with a daily quota | `CHAT_DAILY_QUOTA` (default 20/day per student), HTTP 429 when used up, points can unlock +5 more — `routers/chat.py` |
| Is Elara a local LLM or public? Can it be local? | See §8 — pluggable: `LLM_PROVIDER=ollama` runs fully local |
| Present as a complete project | Role-based navigation, demo data, single-command run, one-click cloud deploy |

---

## 2. Architecture

```
Browser (React + Vite + Tailwind)
   │  JSON over HTTPS, JWT bearer token
   ▼
FastAPI backend ───────────────────────────────────────────────┐
   │ routers/      HTTP endpoints, one file per resource        │
   │ services/     access rules, analytics, roster, gamification│
   │ agent/        LangGraph tutor agent + tools                │
   │ rag/          parse → chunk → topics → vector index        │
   │ llm/          provider-independent LLM interface           │
   ▼                                                            │
SQL database (SQLite locally / PostgreSQL in production)        │
ChromaDB vector store (embedded, on disk)                       │
Redis session cache (optional, in-memory fallback)              │
LLM: mock | Ollama (local) | Gemini | Grok | OpenAI ◄───────────┘
```

In production the backend also serves the built React app, so the whole
project runs as **one web service** (see `Dockerfile`).

### Core flows

1. **Content** — Faculty uploads a file into a subject → `syllabus.py` stores it
   and starts background ingestion → `rag/ingestion.py` extracts text, chunks it,
   asks the LLM for a topic tree (`rag/topic_extraction.py`), saves `Topic` and
   `DocumentChunk` rows and indexes chunk vectors in Chroma.
2. **Registration** — Faculty/Management uploads the Excel roster →
   `services/roster.py` creates student accounts and `Enrollment`s per subject
   and elective.
3. **Learning** — Student opens *My path* → `study_planner.py` builds the plan
   from every topic in their enrolled subjects (`services/access.py`) →
   pre-assessment (`quiz_tools.py`, attempt kind = `pre_assessment`) unlocks the
   study kit → post-preparation test → practice tests. Each submission updates
   mastery, awards points, logs activity.
4. **Elara** — chat message → quota check → LangGraph agent (`agent/graph.py`)
   routes intent → RAG answer limited to the student's own subjects.
5. **Analytics** — `services/analytics.py` turns quiz attempts into per-topic
   score journeys and aggregates them by student / class / subject / elective /
   faculty.

---

## 3. Data model (`backend/app/models.py`)

| Table | Purpose |
|---|---|
| `users` | Everyone. `role` = student / instructor (Faculty) / management. Roster fields: `full_name`, `roll_no`, `class_name`, `must_change_password`, `last_login_at`. |
| `subjects` | Core subjects and electives (`is_elective`), each with one `faculty_id`. |
| `enrollments` | Student ↔ subject. This is how electives are handled. |
| `documents` | Uploaded content, linked to a subject. |
| `document_chunks` | Text chunks (durable copy, used to rebuild the vector index). |
| `topics` | Topic tree extracted from a document. |
| `quiz_attempts` | Every test, with `kind` (pre_assessment / post_preparation / practice), questions, answers, score. |
| `mastery_scores` | Rolling mastery per student per topic. |
| `study_plan_items` | Ordered adaptive plan per student. |
| `chat_messages` | Elara conversation history (also used for the daily quota). |
| `user_sessions` | Study sessions (login + heartbeat). |
| `activity_events` | Log: login, quiz_submitted, study_kit_opened, chat_message, content_uploaded, … |
| `points_transactions` | Points ledger (earned + / spent −). |

Existing databases from the previous version are upgraded automatically on
start (`app/migrations.py` adds the new columns).

---

## 4. File-by-file guide

### Root

| File | Purpose |
|---|---|
| `README.md` | Project summary and quick start. |
| `Dockerfile` | **Single-service image**: builds the frontend, then runs FastAPI which serves both API and web app. Used for online hosting. |
| `render.yaml` | Render.com Blueprint: one-click deploy of the web service + free PostgreSQL. |
| `docker-compose.yml` | Full multi-container local stack: Postgres, Redis, backend, nginx-served frontend. |
| `.env.example` | All configuration variables for Docker Compose (copy to `.env`). |
| `.dockerignore`, `.gitignore` | Keep secrets, builds and data out of images/git. |
| `docs/CODE_DOCUMENTATION.md` | This document. |
| `docs/project_documentation.pdf` | Original architecture / design document. |
| `docs/sample_syllabus.json` | Example course content to upload. |
| `docs/sample_student_roster.xlsx` | Example Excel roster in the expected format. |

### Backend — `backend/`

| File | Purpose |
|---|---|
| `requirements.txt` | Python dependencies. |
| `Dockerfile` | Backend-only image (used by docker-compose). |
| `.env.example` | Config for running the backend without Docker (SQLite + mock LLM by default). |
| `app/main.py` | Creates the FastAPI app, CORS, startup (create tables, upgrade schema, create admin, seed demo data, rebuild vector index), registers routers, serves the built frontend. |
| `app/database.py` | SQLAlchemy engine/session; normalises `postgres://` URLs. |
| `app/models.py` | All database tables (§3). |
| `app/schemas.py` | Pydantic request/response models. |
| `app/migrations.py` | Adds missing columns to an older database on startup. |
| `app/seed.py` | Demo school (3 faculty, 4 subjects incl. 2 electives, 18 students in 2 classes, 3 weeks of activity). `SEED_DEMO=true` or `python -m app.seed`. |
| **core/** | |
| `app/core/config.py` | Every setting, read from environment variables only. |
| `app/core/security.py` | Password hashing (bcrypt), JWT tokens, `get_current_user`, role guards (`require_management`, `require_staff`). |
| `app/core/timeutil.py` | School-timezone "today" for quotas and streaks. |
| `app/core/cache.py` | Redis session cache with in-memory fallback. |
| **routers/** (HTTP API) | |
| `routers/auth.py` | Sign-up (student/faculty), login with **email or roll number**, `/me`, change password. Login starts a session and awards the daily check-in. |
| `routers/syllabus.py` | Faculty content: upload file / add typed notes into a subject, status, list, delete. Students blocked unless `ALLOW_STUDENT_UPLOADS`. |
| `routers/subjects.py` | List/create subjects; management assigns faculty / marks electives. |
| `routers/roster.py` | Excel template download, roster upload, list registered students. |
| `routers/topics.py` | Topics visible to the current user. |
| `routers/study_plan.py` | Build / read the adaptive study plan (with subject, elective flag, pre-assessment status). |
| `routers/quiz.py` | Generate a test (kind decided automatically), submit (grading, mastery, points), explanations. |
| `routers/study_kit.py` | Summary + flashcards + quiz + worked steps for a topic; locked until the pre-assessment is done. |
| `routers/remediation.py` | Micro-lesson when a score is below mastery. |
| `routers/chat.py` | Elara chat (REST + WebSocket), history, daily **quota**, redeem points for more messages. |
| `routers/progress.py` | Per-topic mastery for a student; cohort mastery for faculty. |
| `routers/activity.py` | Heartbeat (sessions), student's own activity report, rewards summary. |
| `routers/faculty.py` | Faculty dashboard: subjects + **limited** per-student metrics, student drill-down. |
| `routers/analytics.py` | Management dashboard: overview, classes, subjects/electives, faculty, students, student detail. |
| **services/** (business logic) | |
| `services/access.py` | Who can see which content (student → enrolled subjects, faculty → taught subjects, management → all). |
| `services/activity.py` | Sessions, events, activity summary. |
| `services/gamification.py` | Points rules, levels, badges, streaks, leaderboard, Elara quota and redemption. |
| `services/analytics.py` | Score journeys and all dashboard aggregations. |
| `services/roster.py` | Excel/CSV parsing, flexible headers, student + enrollment upsert, template generator. |
| **agent/** (LangGraph tutor) | |
| `agent/graph.py` | LangGraph state machine: router node → RAG / quiz / study plan / study kit / remediation / small talk. |
| `agent/router.py` | LLM intent classifier. |
| `agent/state.py` | Agent state type. |
| `agent/study_planner.py` | Orders topics: below-mastery first, then not started, then mastered. |
| `agent/quiz_tools.py` | Quiz generation (validated), grading, mastery update, points + activity hooks, attempt-kind logic. |
| `agent/content_generator.py` | Study kit generation. |
| `agent/remediation.py` | Remediation micro-module + knowledge-gap analysis. |
| **rag/** (retrieval) | |
| `rag/chunking.py` | PDF/text extraction and paragraph-aware chunking. |
| `rag/topic_extraction.py` | LLM → topic tree JSON. |
| `rag/ingestion.py` | Full ingestion pipeline; stores chunks in DB + Chroma. |
| `rag/vector_store.py` | Chroma client; search restricted to allowed documents; rebuilds index from DB on empty disk. |
| `rag/query_engine.py` | Citation-grounded answers with semantic + keyword confidence check. |
| **llm/** (provider-independent) | |
| `llm/base.py` | `LLMProvider` interface: `complete()` and `embed()`. |
| `llm/factory.py` | Picks the provider from `LLM_PROVIDER`. |
| `llm/local_embeddings.py` | Offline hashing embedder (no model download). |
| `llm/providers/ollama_provider.py` | **Local** LLM via Ollama. |
| `llm/providers/gemini_provider.py` | Google Gemini (public, free tier). |
| `llm/providers/grok.py` | xAI Grok (public). |
| `llm/providers/openai_provider.py` | OpenAI or any OpenAI-compatible server (`OPENAI_BASE_URL`). |
| `llm/providers/mock_provider.py` | Keyless deterministic provider for demos/tests. |

### Frontend — `frontend/`

| File | Purpose |
|---|---|
| `package.json`, `vite.config.js`, `index.html` | Build setup (React 19, Vite, Tailwind 4). |
| `Dockerfile`, `nginx.conf` | Frontend-only image for docker-compose. |
| `src/main.jsx` | Entry point: router + auth provider. |
| `src/App.jsx` | All routes, grouped by view, with role guards. `/` sends each role to its home. |
| `src/index.css` | Design tokens (colours, fonts) and shared component classes. |
| `src/lib/api.js` | Every backend call in one place; same-origin in production. |
| `src/context/AuthContext.jsx` | Login state, role home paths, **activity heartbeat** every minute. |
| `src/components/Nav.jsx` | Role-specific navigation (student Upload shown with 🔒). |
| `src/components/ProtectedRoute.jsx` | Redirects if not signed in / wrong role. |
| `src/components/MasteryRing.jsx` | Circular mastery indicator. |
| `src/components/ui.jsx` | Stat cards, tables, tabs, bar charts, score bars, improvement badges. |
| `src/components/StudentReport.jsx` | One student's activity + score journey (used by student, faculty and management). |
| `src/pages/Login.jsx`, `Signup.jsx`, `Account.jsx` | Sign in (email or roll no, demo shortcuts), sign up, change password. |
| `src/pages/Dashboard.jsx` | **Student** home: study path per subject, pre-assessment CTA, points/streak/rank. |
| `src/pages/Quiz.jsx` | Pre-assessment / post-preparation / practice test with improvement and points. |
| `src/pages/StudyKit.jsx` | Study kit (locked until pre-assessment). |
| `src/pages/Chat.jsx` | Elara chat with quota bar and redeem. |
| `src/pages/Progress.jsx` | Student's own activity and improvement. |
| `src/pages/Rewards.jsx` | Points, level, badges, streak, leaderboard, how to earn, redeem. |
| `src/pages/Upload.jsx` | Faculty/Management content manager; greyed-out for students. |
| `src/pages/Roster.jsx` | Excel registration + registered students list. |
| `src/pages/FacultyDashboard.jsx` | **Faculty** dashboard (limited metrics). |
| `src/pages/ManagementDashboard.jsx` | **Management** dashboard with level tabs and CSV export. |
| `src/pages/StudentDetail.jsx` | Student drill-down for faculty / management. |

---

## 5. Running locally

### Option A — quickest (no Docker, SQLite, no API key)

Requirements: Python 3.11, Node 20+.

```bash
# 1. Backend
cd backend
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # defaults: SQLite + mock LLM
# optional: set SEED_DEMO=true in .env to get demo school data
uvicorn app.main:app --reload --port 8000

# 2. Frontend (second terminal)
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

API docs: http://localhost:8000/docs

### Option B — one process, exactly like production

```bash
cd frontend && npm install && npm run build && cd ..
cd backend && source .venv/bin/activate
SEED_DEMO=true uvicorn app.main:app --port 8000
# open http://localhost:8000 — the backend serves the web app too
```

### Option C — Docker

```bash
# single container (same image as the cloud deploy)
docker build -t pathwise .
docker run -p 8000:8000 -e SEED_DEMO=true pathwise

# or the full stack with Postgres + Redis
cp .env.example .env     # set LLM_PROVIDER and keys
docker compose up --build
```

### Demo accounts (when `SEED_DEMO=true`) — password `Demo@1234`

| Role | Login |
|---|---|
| Management | `admin@demo.edu` |
| Faculty | `lakshmi@demo.edu` (Data Structures), `suresh@demo.edu` (DBMS + Cloud elective), `anjali@demo.edu` (ML elective) |
| Student | `student@demo.edu` or roll no `22AD001` |

### First real use (no demo data)

1. Set `ADMIN_EMAIL` / `ADMIN_PASSWORD` → a Management account is created on start.
2. Faculty sign up (role *Faculty*), create their subject(s) and upload content.
3. Faculty/Management download the Excel template on *Students → Registration*,
   fill it and upload. Students sign in with email or roll number; first
   password = roll number.

---

## 6. Putting it online

The repo deploys as **one web service + one database**.

### Render.com (free, recommended)

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → select the repo → **Apply**.
   `render.yaml` creates the Docker web service and a free PostgreSQL database
   and wires `DATABASE_URL` and a random `JWT_SECRET_KEY`.
3. Wait for the build (~5 min). Open the `https://pathwise-xxxx.onrender.com` URL.
4. For real AI answers: in the service's **Environment** tab set
   `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` (free key from Google AI Studio).
5. Before real students use it set `SEED_DEMO=false` and `ADMIN_EMAIL`/`ADMIN_PASSWORD`.

Notes for free tiers: the service sleeps after ~15 min idle (first request
takes ~30–60 s to wake). The disk is temporary, which is why chunks are also
stored in the database and the vector index is rebuilt automatically on start;
uploaded original files are not needed after ingestion. Render's free
PostgreSQL is time-limited (30 days at the time of writing) — upgrade or move
to another Postgres for long-term use.

### Any other Docker host

Railway, Fly.io, Hugging Face Spaces, Azure/AWS/GCP or a college server: build
the root `Dockerfile`, set `DATABASE_URL` (PostgreSQL), `JWT_SECRET_KEY` and the
LLM variables. The container listens on `$PORT` (default 8000).

---

## 7. Motivation design — why students self-assess

| Mechanism | Detail |
|---|---|
| Pre-assessment is the way in | Study kit unlocks only after the topic's pre-assessment; the button shows "+10 pts". |
| Improvement beats raw score | +1 point per % gained over your previous attempt (max +30/test) — weaker students can out-earn stronger ones. |
| Mastery bonus | +25 the first time a topic reaches 75 %. |
| Habit | Daily check-in +2, +3/day extra on a 3-day streak, streak counter on the dashboard. |
| Spendable credits | 20 points → +5 Elara messages today, so points have real value. |
| Status | Levels (every 100 points), 7 badges, class leaderboard and rank. |

All values are in `POINT_RULES` (`services/gamification.py`) and the `.env`
quota settings.

---

## 8. Elara: local or public LLM?

Elara is **provider-independent**. Every AI call goes through `LLMProvider`;
switching is one environment variable, no code change:

| `LLM_PROVIDER` | Where the model runs | Data leaves the institution? | Cost |
|---|---|---|---|
| `ollama` | **Local** — Llama 3 / Mistral / Qwen on your own server via Ollama | No | Hardware only |
| `gemini` | Google cloud | Yes | Free tier available |
| `grok` / `openai` | xAI / OpenAI cloud | Yes | Paid per token |
| `mock` | No model (placeholder text) | No | Free |

**Making it local:** install Ollama on a machine with ~8 GB RAM (16 GB+ or a
GPU recommended), `ollama pull llama3`, then set `LLM_PROVIDER=ollama`,
`OLLAMA_BASE_URL=http://<server>:11434`, `OLLAMA_MODEL=llama3`. Retrieval
embeddings are already computed locally (`llm/local_embeddings.py`) for every
provider except OpenAI, so with Ollama no student data leaves the network.
Trade-off: a local 8B model is slower and somewhat less accurate than large
cloud models, and free cloud hosting cannot run it — host the backend on the
institution's server when using Ollama.

Access is limited per student per day (`CHAT_DAILY_QUOTA`), which controls
cost on public providers and load on a local one.

---

## 9. API overview

Interactive docs at `/docs`. Main groups:

| Prefix | Who | Purpose |
|---|---|---|
| `/auth` | all | signup, login (email or roll no), me, change-password |
| `/subjects` | all / staff / mgmt | subjects and electives |
| `/roster` | faculty, mgmt | Excel template, upload, registered students |
| `/syllabus` | faculty, mgmt | content upload / notes / list / delete |
| `/study-plan`, `/topics`, `/quiz`, `/study-kit`, `/remediation` | students | learning loop |
| `/chat` | students, faculty | Elara, quota, redeem |
| `/activity`, `/rewards` | students | heartbeat, own report, rewards |
| `/faculty-dashboard` | faculty | limited student metrics |
| `/analytics` | management | institution metrics |
| `/health`, `/config/public` | anyone | health check, feature flags |

## 10. Metric definitions

* **Pre-assessment score** — first test a student takes on a topic (before the study kit).
* **Post-preparation score** — second test on that topic (after studying).
* **Consecutive scores** — third and later tests.
* **Improvement** — latest score − pre-assessment score (only topics with ≥ 2 tests).
* **Mastered** — latest score ≥ 75 %.
* **Focus areas** — a student's topics with latest score < 75 %, weakest first.
* **Session** — continuous use; a gap of more than 30 minutes without the app open starts a new one.
* **Active (7 days)** — had a session in the last 7 days.
