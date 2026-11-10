"""
Who can see which content.

* student     -> documents of the subjects they're enrolled in (+ anything they uploaded)
* instructor  -> documents of the subjects they teach (+ anything they uploaded)
* management  -> everything

Every topic/RAG query goes through these helpers, so the rule lives in one place.
"""
from sqlalchemy.orm import Session

from app import models


def subject_ids_for_user(db: Session, user: models.User) -> list[str] | None:
    """Subject ids the user is scoped to. None means "all subjects" (management)."""
    if user.role == models.RoleEnum.management:
        return None
    if user.role == models.RoleEnum.instructor:
        return [s.id for s in db.query(models.Subject.id).filter(models.Subject.faculty_id == user.id)]
    return [
        e.subject_id
        for e in db.query(models.Enrollment.subject_id).filter(models.Enrollment.user_id == user.id)
    ]


def accessible_document_query(db: Session, user: models.User):
    q = db.query(models.Document)
    subject_ids = subject_ids_for_user(db, user)
    if subject_ids is None:
        return q
    cond = models.Document.user_id == user.id
    if subject_ids:
        cond = cond | models.Document.subject_id.in_(subject_ids)
    return q.filter(cond)


def accessible_document_ids(db: Session, user_or_id) -> list[str]:
    user = user_or_id
    if isinstance(user_or_id, str):
        user = db.query(models.User).filter(models.User.id == user_or_id).first()
        if not user:
            return []
    return [d.id for d in accessible_document_query(db, user).filter(models.Document.status == "ready")]


def accessible_topics_query(db: Session, user: models.User):
    doc_ids = [d.id for d in accessible_document_query(db, user)]
    return (
        db.query(models.Topic)
        .filter(models.Topic.document_id.in_(doc_ids or ["__none__"]))
        .order_by(models.Topic.document_id, models.Topic.order_index)
    )
