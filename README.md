# Personalized Learning Path Generator

An AI-powered adaptive tutor: uploads a syllabus, builds a knowledge graph,
generates a study plan, and runs a full agentic loop of quizzing, mastery
tracking, and remediation — grounded by RAG over your own course material.
Built from the team's [project documentation](./docs/) architecture.

## Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| Agent framework | LangGraph / LangChain |
| LLM | Pluggable: Grok (xAI), OpenAI, Ollama (local), or a keyless mock for dev |
| Relational data | PostgreSQL 15 |
| Vector store | ChromaDB (embedded, persisted volume) |
| Session cache | Redis |
| Auth | JWT (bcrypt password hashing) |

## Provider-independent LLM layer

Every tool, the RAG engine, and the LangGraph agent talk to `LLMProvider`, an
interface with two methods: `complete()` and `embed()`. Swapping providers is
a single environment variable — **no application code changes**:

```env
LLM_PROVIDER=grok      # or: openai | ollama | mock
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

## Quick start — Docker (recommended, matches the full architecture)

```bash
cp .env.example .env
# edit .env: set LLM_PROVIDER and the matching API key
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000/docs
- Postgres: localhost:5432, Redis: localhost:6379 (both persisted to named volumes)

> Docker wasn't available in the environment this was built in, so the
> compose file is written and reviewed but not container-tested end-to-end
> here — the backend and frontend were run and fully verified directly (see
> below), which exercises the same application code. Sanity-check
> `docker compose up` on your machine and open an issue/ping the team with
> any environment-specific hiccup.

## Quick start — run locally without Docker (fastest inner loop)

This is how the app was actually developed and tested — SQLite instead of
Postgres, ChromaDB embedded to a local folder, no Redis required.

**Backend:**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# For a quick test with no API key at all:
#   LLM_PROVIDER=mock
#   DATABASE_URL=sqlite:///./tutor.db
uvicorn app.main:app --reload --port 8000
```

**Frontend** (new terminal):
```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Visit http://localhost:5173, sign up, and upload `docs/sample_syllabus.json`
(or your own PDF/JSON syllabus) to try the full flow.

## What's implemented

- **Auth** — signup/login, JWT, bcrypt hashing, student/instructor roles
- **Ingestion pipeline** — PDF/JSON/text upload → chunking → LLM topic
  extraction → knowledge graph (Postgres) + embeddings (Chroma)
- **RAG chat** — hybrid semantic + keyword retrieval, citation-grounded
  answers, declines when retrieval confidence is low
- **Adaptive study planner** — orders topics by mastery/attempt history
- **Quiz generator/evaluator** — auto-scored, per-question wrong-answer
  explanations, mastery-score gating
- **Remediation** — auto-triggered micro-learning module when a quiz score
  falls below the mastery threshold
- **Multi-modal study kits** — summary, flashcards, quiz, step-by-step guide
  in one generation call
- **Progress dashboards** — per-topic mastery for students; aggregated
  cohort view for instructors
- **LangGraph agent** — tool-router classifies intent and dispatches to the
  right tutor tool or the RAG engine

## Project layout

```
backend/
  app/
    core/          # settings, JWT/password security
    llm/            provider-independent LLM interface + Grok/OpenAI/Ollama/mock
    rag/            chunking, ingestion, vector store, topic extraction
    agent/          LangGraph tutor agent + tools (quiz, study plan, content gen, remediation)
    routers/        FastAPI endpoints (one file per resource)
    models.py        SQLAlchemy models
    schemas.py        Pydantic request/response schemas
frontend/
  src/
    pages/          one file per screen (Dashboard, Chat, Quiz, StudyKit, Progress, Upload, Auth)
    components/      Nav, MasteryRing, ProtectedRoute
    lib/api.js       typed fetch client
    context/         auth context
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
- Cohort dashboard is a flat per-topic average; no per-student drill-down yet.
- No automated test suite yet — everything was verified with manual/curl
  integration tests during development (see git history / build notes).
