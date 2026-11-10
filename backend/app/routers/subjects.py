"""Subjects (core papers and electives) and who teaches them."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.security import get_current_user, require_management, require_staff
from app.database import get_db

router = APIRouter(prefix="/subjects", tags=["subjects"])


class SubjectCreate(BaseModel):
    code: str
    name: str
    is_elective: bool = False


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    is_elective: Optional[bool] = None
    faculty_id: Optional[str] = None


def _out(s: models.Subject) -> dict:
    return {
        "id": s.id,
        "code": s.code,
        "name": s.name,
        "is_elective": bool(s.is_elective),
        "faculty_id": s.faculty_id,
        "faculty": s.faculty.display_name if s.faculty else None,
        "enrolled": len(s.enrollments),
        "content_items": len(s.documents),
    }


@router.get("/")
def list_subjects(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Students: their enrolled subjects. Faculty: theirs + unassigned ones. Management: all."""
    q = db.query(models.Subject)
    if current_user.role == models.RoleEnum.student:
        q = q.join(models.Enrollment).filter(models.Enrollment.user_id == current_user.id)
    elif current_user.role == models.RoleEnum.instructor:
        q = q.filter((models.Subject.faculty_id == current_user.id) | (models.Subject.faculty_id.is_(None)))
    return [_out(s) for s in q.order_by(models.Subject.is_elective, models.Subject.code).all()]


@router.post("/", status_code=201)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff),
):
    code = payload.code.strip().upper()
    if not code or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Subject code and name are required")
    if db.query(models.Subject).filter(func.lower(models.Subject.code) == code.lower()).first():
        raise HTTPException(status_code=400, detail=f"Subject {code} already exists")
    subject = models.Subject(
        code=code, name=payload.name.strip(), is_elective=payload.is_elective,
        faculty_id=current_user.id if current_user.role == models.RoleEnum.instructor else None,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _out(subject)


@router.patch("/{subject_id}")
def update_subject(
    subject_id: str,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_management),
):
    """Management: rename, flag as elective, or assign the faculty member."""
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if payload.name is not None:
        subject.name = payload.name
    if payload.is_elective is not None:
        subject.is_elective = payload.is_elective
    if payload.faculty_id is not None:
        if payload.faculty_id == "":
            subject.faculty_id = None
        else:
            fac = db.query(models.User).filter(
                models.User.id == payload.faculty_id, models.User.role == models.RoleEnum.instructor
            ).first()
            if not fac:
                raise HTTPException(status_code=404, detail="Faculty member not found")
            subject.faculty_id = fac.id
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return _out(subject)


@router.get("/faculty-list")
def faculty_list(db: Session = Depends(get_db), current_user: models.User = Depends(require_management)):
    return [
        {"id": f.id, "name": f.display_name, "email": f.email}
        for f in db.query(models.User).filter(models.User.role == models.RoleEnum.instructor)
    ]
