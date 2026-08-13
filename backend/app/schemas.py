from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- Topics / Study plan ----
class TopicOut(BaseModel):
    id: str
    title: str
    difficulty: str
    order_index: int
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class StudyPlanItemOut(BaseModel):
    id: str
    topic_id: str
    topic_title: str
    status: str
    scheduled_order: int
    reason: Optional[str] = None

    class Config:
        from_attributes = True


# ---- Quiz ----
class QuizGenerateRequest(BaseModel):
    topic_id: str
    num_questions: int = 5


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_index: int


class QuizOut(BaseModel):
    quiz_id: str
    topic_id: str
    questions: list[dict]  # options only, no correct_index sent to client


class QuizSubmitRequest(BaseModel):
    quiz_id: str
    answers: list[int]


class QuizResultOut(BaseModel):
    quiz_id: str
    score: float
    mastery_score: float
    passed: bool
    explanations: list[dict]
    remediation_triggered: bool


# ---- Study Kit ----
class StudyKitRequest(BaseModel):
    topic_id: str


class StudyKitOut(BaseModel):
    topic_id: str
    summary: str
    flashcards: list[dict]
    quiz: list[dict]
    step_by_step_guide: list[str]


# ---- Remediation ----
class RemediationRequest(BaseModel):
    topic_id: str
    sub_concept: Optional[str] = None


class RemediationOut(BaseModel):
    topic_id: str
    micro_module: str
    explanation: str
    resources: list[dict] = []


# ---- Chat ----
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    role: str
    content: str
    citations: list[dict] = []


# ---- Progress ----
class ProgressTrend(BaseModel):
    topic_id: str
    topic_title: str
    score: float
    attempts: int
    status: str


class ProgressOut(BaseModel):
    overall_mastery: float
    trends: list[ProgressTrend]
