# Personalized Learning Path Generator (Pathwise)

An AI-powered adaptive tutor with **Student, Faculty and Management views**.
Faculty upload course content into subjects and register students from an
Excel sheet; students self-assess, study AI-generated kits, re-test and chat
with **Elara**, the AI tutor; management tracks improvement across classes,
subjects, electives, faculty and individual students.

📘 **Full code documentation** (purpose of every file, run & deploy steps, metric
definitions, local-vs-public LLM): [`docs/CODE_DOCUMENTATION.md`](./docs/CODE_DOCUMENTATION.md)

## Try it in 2 minutes

```bash
cd frontend && npm install && npm run build && cd ../backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
SEED_DEMO=true LLM_PROVIDER=mock uvicorn app.main:app --port 8000
```

Open http://localhost:8000 and use a demo login (password `Demo@1234`):
`admin@demo.edu` (Management) · `lakshmi@demo.edu` (Faculty) · `student@demo.edu` (Student).

## Put it online

`render.yaml` + the root `Dockerfile` deploy the whole app as one web service
with a free PostgreSQL database: Render → **New → Blueprint** → pick this repo.
Details and other hosts: [docs §6](./docs/CODE_DOCUMENTATION.md#6-putting-it-online).

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| Agent framework | LangGraph / LangChain |
| LLM | Pluggable: Ollama (local), Gemini, Grok (xAI), OpenAI, or a keyless mock |
| Relational data | PostgreSQL 15 |
| Vector store | ChromaDB (embedded, persisted volume) |
| Session cache | Redis |
| Auth | JWT (bcrypt password hashing) |

## Provider-independent LLM layer

Every tool, the RAG engine, and the LangGraph agent talk to `LLMProvider`, an
interface with two methods: `complete()` and `embed()`. Swapping providers is
a single environment variable — **no application code changes**:

```env
LLM_PROVIDER=grok      # or: gemini | openai | ollama | mock
GROK_API_KEY=xai-...
OPENAI_API_KEY=sk-...
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

API keys are **only** ever read from environment variables
(`backend/app/core/config.py`) — never hardcoded, never logged. `.env` is
git-ignored; only `.env.example` (no real values) is committed.

`LLM_PROVIDER=mock` runs a deterministic, keyless provider that returns
structurally-valid responses for every tool — useful for local development,
demos, and CI without spending API credits.

## Other ways to run

See [docs §5](./docs/CODE_DOCUMENTATION.md#5-running-locally): dev mode with hot
reload (`npm run dev` + `uvicorn --reload`), single Docker container, or the
full `docker compose` stack with Postgres and Redis.

## What's implemented

**Roles & views**
- **Student** — study path per enrolled subject/elective, pre-assessment →
  study kit → post-preparation test → practice tests, Elara chat with a daily
  quota, *My progress* (logins, sessions, scores, improvement), *Rewards*
  (points, levels, badges, streaks, class leaderboard). Own uploads are shown
  but greyed out.
- **Faculty** — upload files or type notes into their subjects, Excel/CSV
  student registration (email, roll/admission no, class, subjects, electives),
  dashboard with limited per-student metrics and drill-down.
- **Management** — metric dashboard at overview, class, subject, elective,
  faculty and student level: pre-assessment, post-preparation and consecutive
  scores, improvement, focus areas, CSV export, faculty assignment.

**Platform**
- **Auth** — JWT, bcrypt, login with email or roll number, forced password change after roster registration
- **Ingestion pipeline** — PDF/JSON/text upload or typed notes → chunking → LLM topic
  extraction → knowledge graph (SQL) + embeddings (Chroma, rebuildable from SQL)
- **Elara RAG chat** — semantic + keyword retrieval restricted to the student's
  subjects, citation-grounded answers, declines when confidence is low
- **Adaptive study planner**, **quiz generator/evaluator**, **remediation**, **multi-modal study kits**
- **Activity tracking** — sessions via login + heartbeat, event log
- **Motivation** — points ledger, levels, badges, streaks, leaderboard; points buy extra Elara messages
- **LangGraph agent** — tool-router classifies intent and dispatches to the right tool or the RAG engine

## Project layout

```
backend/
  app/
    core/          # settings, JWT/password security
    llm/            provider-independent LLM interface + Grok/OpenAI/Ollama/mock
    rag/            chunking, ingestion, vector store, topic extraction
    agent/          LangGraph tutor agent + tools (quiz, study plan, content gen, remediation)
    services/       access rules, analytics, roster import, gamification, activity
    routers/        FastAPI endpoints (one file per resource)
    models.py        SQLAlchemy models
    schemas.py        Pydantic request/response schemas
frontend/
  src/
    pages/          one file per screen (Dashboard, Chat, Quiz, StudyKit, Progress, Upload, Auth)
    components/      Nav, MasteryRing, ProtectedRoute
    lib/api.js       typed fetch client
    context/         auth context
docs/CODE_DOCUMENTATION.md   file-by-file documentation
Dockerfile         single-service image (frontend + backend) for hosting
render.yaml        one-click Render deploy
docker-compose.yml
.env.example
```

## Known limitations / next steps

- The mock LLM provider produces structurally-correct but not "smart"
  content — swap in a real provider for meaningful answers.
- Chat currently uses the REST `/chat/message` endpoint; the WebSocket
  `/chat/ws` streaming endpoint exists on the backend but the frontend isn't
  wired to it yet (easy follow-up: swap the `fetch` call for a `WebSocket`
  in `src/pages/Chat.jsx`).
- No automated test suite yet — flows were verified with scripted
  end-to-end API calls and browser checks.
- Schema changes use a small built-in column upgrader (`app/migrations.py`);
  switch to Alembic if the schema keeps growing.
