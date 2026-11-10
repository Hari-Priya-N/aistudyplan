"""
Course content upload (Faculty view: "add and upload content").

Faculty upload a PDF/JSON/TXT file — or paste notes — into one of their
subjects. Ingestion (parse -> chunk -> topic extraction -> vector index) runs
in the background. Every student enrolled in that subject then sees the
topics on their dashboard.

Students cannot upload by default (ALLOW_STUDENT_UPLOADS=false): the upload
page is shown to them greyed out, and this endpoint refuses with 403.
"""
import os
import re
import shutil
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.core.security import get_current_user
from app.database import get_db, SessionLocal
from app.rag.ingestion import ingest_document
from app.rag.vector_store import delete_document_chunks
from app.services.activity import record_event


def _run_ingestion_in_background(document_id: str, file_path: str, user_id: str):
    """
    Background tasks may outlive the request-scoped DB session, so this opens
    its own session rather than reusing the one injected into the endpoint.
    """
    task_db = SessionLocal()
    try:
        document = task_db.query(models.Document).filter(models.Document.id == document_id).first()
        if document:
            try:
                ingest_document(task_db, document, file_path, user_id)
            except Exception:  # status already set to "failed" inside ingest_document
                pass
    finally:
        task_db.close()


router = APIRouter(prefix="/syllabus", tags=["syllabus"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".json", ".txt", ".md"}


def _check_can_upload(db: Session, user: models.User, subject_id: Optional[str]) -> Optional[models.Subject]:
    if user.role == models.RoleEnum.student:
        if not get_settings().allow_student_uploads:
            raise HTTPException(
                status_code=403,
                detail="Uploading your own material isn't enabled yet — your faculty adds course content.",
            )
        return None
    if not subject_id:
        raise HTTPException(status_code=400, detail="Choose the subject this content belongs to")
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if user.role == models.RoleEnum.instructor:
        if subject.faculty_id and subject.faculty_id != user.id:
            raise HTTPException(status_code=403, detail="That subject is assigned to another faculty member")
        if not subject.faculty_id:  # unassigned subject: the uploading faculty takes it
            subject.faculty_id = user.id
            db.add(subject)
    return subject


def _create_document(db: Session, user: models.User, subject: Optional[models.Subject], filename: str) -> models.Document:
    document = models.Document(
        user_id=user.id, subject_id=subject.id if subject else None, filename=filename, status="processing"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    record_event(db, user.id, "content_uploaded", {"document_id": document.id, "filename": filename})
    return document


@router.post("/upload")
def upload_syllabus(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")
    subject = _check_can_upload(db, current_user, subject_id)
    document = _create_document(db, current_user, subject, file.filename)

    saved_path = os.path.join(UPLOAD_DIR, f"{document.id}_{os.path.basename(file.filename)}")
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingestion (parsing, chunking, topic extraction, vectorization) runs in the
    # background so the upload request returns immediately with a "processing" status.
    background_tasks.add_task(_run_ingestion_in_background, document.id, saved_path, current_user.id)
    return {"document_id": document.id, "status": document.status}


class TextContentRequest(BaseModel):
    subject_id: str
    title: str
    content: str


@router.post("/text")
def add_text_content(
    payload: TextContentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Faculty can also type/paste notes directly instead of uploading a file."""
    if len(payload.content.strip()) < 40:
        raise HTTPException(status_code=400, detail="Add a little more content (at least a few sentences)")
    subject = _check_can_upload(db, current_user, payload.subject_id)
    safe = re.sub(r"[^A-Za-z0-9_\- ]+", "", payload.title).strip() or "notes"
    document = _create_document(db, current_user, subject, f"{safe}.txt")
    saved_path = os.path.join(UPLOAD_DIR, f"{document.id}_{safe.replace(' ', '_')}.txt")
    with open(saved_path, "w", encoding="utf-8") as f:
        f.write(f"{payload.title}\n\n{payload.content}")
    background_tasks.add_task(_run_ingestion_in_background, document.id, saved_path, current_user.id)
    return {"document_id": document.id, "status": document.status}


def _owned_or_managed(db: Session, user: models.User, document_id: str) -> models.Document:
    q = db.query(models.Document).filter(models.Document.id == document_id)
    if user.role != models.RoleEnum.management:
        q = q.filter(models.Document.user_id == user.id)
    document = q.first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/status")
def get_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    document = _owned_or_managed(db, current_user, document_id)
    return {"document_id": document.id, "status": document.status, "topics": len(document.topics)}


@router.get("/", response_model=list[dict])
def list_documents(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    q = db.query(models.Document)
    if current_user.role != models.RoleEnum.management:
        q = q.filter(models.Document.user_id == current_user.id)
    docs = q.order_by(models.Document.uploaded_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "status": d.status,
            "uploaded_at": d.uploaded_at,
            "subject": f"{d.subject.code} · {d.subject.name}" if d.subject else None,
            "topics": len(d.topics),
        }
        for d in docs
    ]


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    document = _owned_or_managed(db, current_user, document_id)
    topic_ids = [t.id for t in document.topics]
    if topic_ids:  # remove rows that reference this document's topics first
        for model in (models.StudyPlanItem, models.MasteryScore, models.QuizAttempt):
            db.query(model).filter(model.topic_id.in_(topic_ids)).delete(synchronize_session=False)
        db.query(models.Topic).filter(models.Topic.document_id == document.id).update(
            {models.Topic.parent_id: None}, synchronize_session=False
        )
    try:
        delete_document_chunks(document_id)
    except Exception:
        pass
    db.delete(document)
    db.commit()
    return {"status": "deleted"}
