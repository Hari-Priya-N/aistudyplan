from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr


# ---- Auth ----
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: str = "student"          # "student" | "faculty" (alias "instructor")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    # Email OR roll/admission number (students registered from the Excel roster)
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    created_at: datetime
    full_name: Optional[str] = None
    roll_no: Optional[str] = None
    class_name: Optional[str] = None
    must_change_password: bool = False

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
    subject_name: Optional[str] = None
    is_elective: bool = False
    has_pre_assessment: bool = False
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
    kind: str = "practice"   # pre_assessment | post_preparation | practice
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
    kind: str = "practice"
    previous_score: Optional[float] = None
    points_awarded: list[dict] = []


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
    quota: Optional[dict] = None


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
