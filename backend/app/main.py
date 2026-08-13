from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.database import Base, engine
from app.routers import auth, syllabus, study_plan, quiz, study_kit, remediation, chat, progress, topics

settings = get_settings()

app = FastAPI(
    title="Personalized Learning Path Generator API",
    version="1.0.0",
    description="AI-powered agentic tutor backend (FastAPI + LangGraph + RAG).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider}


app.include_router(auth.router)
app.include_router(syllabus.router)
app.include_router(study_plan.router)
app.include_router(quiz.router)
app.include_router(study_kit.router)
app.include_router(remediation.router)
app.include_router(chat.router)
app.include_router(progress.router)
app.include_router(topics.router)
