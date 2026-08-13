import os
import shutil
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import get_current_user
from app.database import get_db, SessionLocal
from app.rag.ingestion import ingest_document
from app.rag.vector_store import delete_document_chunks


def _run_ingestion_in_background(document_id: str, file_path: str, user_id: str):
    """
    Background tasks may outlive the request-scoped DB session, so this opens
    its own session rather than reusing the one injected into the endpoint.
    """
    task_db = SessionLocal()
    try:
        document = task_db.query(models.Document).filter(models.Document.id == document_id).first()
        if document:
            ingest_document(task_db, document, file_path, user_id)
    finally:
        task_db.close()

router = APIRouter(prefix="/syllabus", tags=["syllabus"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "./data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".json", ".txt"}


@router.post("/upload")
def upload_syllabus(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    document = models.Document(user_id=current_user.id, filename=file.filename, status="processing")
    db.add(document)
    db.commit()
    db.refresh(document)

    saved_path = os.path.join(UPLOAD_DIR, f"{document.id}_{file.filename}")
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Ingestion (parsing, chunking, topic extraction, vectorization) runs in the
    # background so the upload request returns immediately with a "processing" status.
    background_tasks.add_task(_run_ingestion_in_background, document.id, saved_path, current_user.id)

    return {"document_id": document.id, "status": document.status}


@router.get("/{document_id}/status")
def get_status(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id, models.Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document_id": document.id, "status": document.status}


@router.get("/", response_model=list[dict])
def list_documents(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    docs = db.query(models.Document).filter(models.Document.user_id == current_user.id).all()
    return [
        {"id": d.id, "filename": d.filename, "status": d.status, "uploaded_at": d.uploaded_at}
        for d in docs
    ]


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id, models.Document.user_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    delete_document_chunks(document_id)
    db.delete(document)
    db.commit()
    return {"status": "deleted"}
