import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, ForeignKey, DateTime, Text, Enum, JSON, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    student = "student"
    instructor = "instructor"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    mastery_scores = relationship("MasteryScore", back_populates="user", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    study_plan_items = relationship("StudyPlanItem", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    status = Column(String, default="processing")  # processing | ready | failed
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="documents")
    topics = relationship("Topic", back_populates="document", cascade="all, delete-orphan")


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


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=False)
    questions = Column(JSON, nullable=False)   # list of {question, options, correct_index}
    answers = Column(JSON, nullable=True)      # list of selected indices
    score = Column(Float, nullable=True)       # 0.0 - 1.0
    explanations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
