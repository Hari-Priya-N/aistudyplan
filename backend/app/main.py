import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import models
from app.core.config import get_settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.migrations import upgrade_schema
from app.routers import (
    activity, analytics, auth, chat, faculty, progress, quiz, remediation, roster, study_kit,
    study_plan, subjects, syllabus, topics,
)

settings = get_settings()
log = logging.getLogger("pathwise")

app = FastAPI(
    title="Personalized Learning Path Generator API",
    version="2.0.0",
    description="AI-powered agentic tutor backend (FastAPI + LangGraph + RAG) "
                "with Student, Faculty and Management views.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _bootstrap_admin(db):
    """Create/refresh a management account from ADMIN_EMAIL / ADMIN_PASSWORD, if set."""
    if not (settings.admin_email and settings.admin_password):
        return
    email = settings.admin_email.lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        db.add(models.User(email=email, hashed_password=hash_password(settings.admin_password),
                           role=models.RoleEnum.management, full_name="Management"))
        db.commit()
        log.info("Created management account %s", email)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    applied = upgrade_schema(engine)
    if applied:
        log.info("Schema upgraded: %s", ", ".join(applied))

    from app.llm.factory import get_llm_provider
    from app.llm.local_embeddings import embed_texts
    from app.rag.vector_store import rebuild_index_if_empty

    def embed(texts):
        try:
            return get_llm_provider().embed(texts)
        except Exception:
            return embed_texts(texts)

    db = SessionLocal()
    try:
        _bootstrap_admin(db)
        if settings.seed_demo:
            from app.seed import seed_demo
            if seed_demo(db, embed):
                log.info("Demo data created (see app/seed.py for the demo logins)")
        try:
            n = rebuild_index_if_empty(db, embed)
            if n:
                log.info("Rebuilt vector index from %d stored chunks", n)
        except Exception as exc:  # never block startup on the vector index
            log.warning("Vector index rebuild skipped: %s", exc)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}


@app.get("/config/public")
def public_config():
    """Non-secret settings the web app needs (feature flags, limits)."""
    return {
        "allow_student_uploads": settings.allow_student_uploads,
        "chat_daily_quota": settings.chat_daily_quota,
        "llm_provider": settings.llm_provider,
        "llm_is_local": settings.llm_provider in ("ollama", "mock"),
        "demo": settings.seed_demo,
    }


for r in (auth, syllabus, study_plan, quiz, study_kit, remediation, chat, progress, topics,
          subjects, roster, analytics, faculty, activity):
    app.include_router(r.router)


# ---------------------------------------------------------------------------
# Serve the built React app from the same server (single-service deployment).
# Registered LAST so every API route above takes precedence; any other GET
# returns a static file or index.html so client-side routes survive a refresh.
# ---------------------------------------------------------------------------
def _static_dir() -> Path | None:
    candidates = [settings.static_dir, os.environ.get("STATIC_DIR", ""), "static",
                  str(Path(__file__).resolve().parents[2] / "frontend" / "dist")]
    for c in candidates:
        if c and (Path(c) / "index.html").is_file():
            return Path(c).resolve()
    return None


STATIC_DIR = _static_dir()

if STATIC_DIR:
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith(("docs", "openapi.json", "redoc")):
            raise HTTPException(status_code=404)
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and STATIC_DIR in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
