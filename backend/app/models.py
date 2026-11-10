"""
SQLAlchemy ORM models — every table the application uses.

Roles
-----
* student     — learns: takes pre-assessments/quizzes, uses study kits and Elara chat.
* instructor  — shown as "Faculty" in the UI: uploads content, registers students
                (Excel roster), sees limited per-student metrics for their subjects.
* management  — school management: read-only metric dashboards across classes,
                subjects, students, faculty and electives.

Content visibility
------------------
Faculty upload content into a *Subject*. Students see every topic from the
subjects they are enrolled in (core subjects + their electives), which is what
the Excel roster upload sets up.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, ForeignKey, DateTime, Text, Enum, JSON, Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    student = "student"
    instructor = "instructor"   # "Faculty" in the UI
    management = "management"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Profile / registration fields (filled by the Excel roster upload)
    full_name = Column(String, nullable=True)
    roll_no = Column(String, nullable=True, index=True)        # roll no / admission no
    class_name = Column(String, nullable=True, index=True)     # e.g. "CSE-3A"
    must_change_password = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    mastery_scores = relationship("MasteryScore", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    study_plan_items = relationship("StudyPlanItem", back_populates="user", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="user", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        return self.full_name or self.email.split("@")[0]


class Subject(Base):
    """A course/paper. Core or elective. Owned (taught) by one faculty member."""
    __tablename__ = "subjects"

    id = Column(String, primary_key=True, default=gen_uuid)
    code = Column(String, unique=True, index=True, nullable=False)   # e.g. "CS201"
    name = Column(String, nullable=False)
    is_elective = Column(Boolean, default=False)
    faculty_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    faculty = relationship("User", foreign_keys=[faculty_id])
    enrollments = relationship("Enrollment", back_populates="subject", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="subject")


class Enrollment(Base):
    """Student <-> Subject link (this is how electives are handled)."""
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "subject_id", name="uq_enrollment"),)

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="enrollments")
    subject = relationship("Subject", back_populates="enrollments")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    subject_id = Column(String, ForeignKey("subjects.id"), nullable=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="processing")  # processing | ready | failed
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    subject = relationship("Subject", back_populates="documents")
    topics = relationship("Topic", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    Text chunks are kept in the relational DB as well as in Chroma, so the
    vector index can be rebuilt automatically on hosts with an ephemeral disk
    (e.g. free cloud tiers) — see app/rag/vector_store.rebuild_index_if_empty.
    """
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, default=gen_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    parent_id = Column(String, ForeignKey("topics.id"), nullable=True)
    title = Column(String, nullable=False)
    difficulty = Column(String, default="medium")  # easy | medium | hard
    order_index = Column(Integer, default=0)

    document = relationship("Document", back_populates="topics")
    children = relationship("Topic", backref="parent", remote_side=[id])


class MasteryScore(Base):
    __tablename__ = "mastery_scores"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    score = Column(Float, default=0.0)  # 0.0 - 1.0
    attempts = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="mastery_scores")
    topic = relationship("Topic")


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    status = Column(String, default="pending")  # pending | in_progress | mastered | needs_remediation
    scheduled_order = Column(Integer, default=0)
    reason = Column(Text, nullable=True)  # why the agent scheduled this next
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="study_plan_items")
    topic = relationship("Topic")


class QuizKind(str, enum.Enum):
    pre_assessment = "pre_assessment"        # 1st attempt — before studying the topic
    post_preparation = "post_preparation"    # 2nd attempt — after topic preparation
    practice = "practice"                    # 3rd+ attempts — "consecutive scores"


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    kind = Column(String, default=QuizKind.practice.value)
    questions = Column(JSON, nullable=False)   # list of {question, options, correct_index}
    answers = Column(JSON, nullable=True)      # list of selected indices
    score = Column(Float, nullable=True)       # 0.0 - 1.0 (None until submitted)
    explanations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="quiz_attempts")
    topic = relationship("Topic")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    citations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_messages")


# --------------------------------------------------------------------------
# Activity tracking (logins, sessions, actions)
# --------------------------------------------------------------------------
class UserSession(Base):
    """A continuous period of use. Started at login; extended by frontend heartbeats."""
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class ActivityEvent(Base):
    """Append-only log: login, quiz_submitted, study_kit_opened, chat_message, ..."""
    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# --------------------------------------------------------------------------
# Motivation: credit points ledger
# --------------------------------------------------------------------------
class PointsTransaction(Base):
    """Every point earned (+) or spent (-). Balance = SUM(points)."""
    __tablename__ = "points_transactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    points = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)       # machine code, e.g. "pre_assessment"
    description = Column(String, nullable=True)   # human text shown in the UI
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
