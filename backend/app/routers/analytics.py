"""
Management view — predominantly a metric dashboard (read-only).

Levels: overview, class, subject, elective, faculty, student (+ drill-down).
Every level shows pre-assessment, post-preparation and latest (consecutive)
scores, with the focus on improvement and each student's focus areas.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.core.security import require_management
from app.database import get_db
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["management analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: models.User = Depends(require_management)):
    return analytics.overview(db)


@router.get("/classes")
def classes(db: Session = Depends(get_db), _: models.User = Depends(require_management)):
    return analytics.by_class(db)


@router.get("/subjects")
def subjects(elective: Optional[bool] = None, db: Session = Depends(get_db),
             _: models.User = Depends(require_management)):
    return analytics.by_subject(db, elective)


@router.get("/faculty")
def faculty(db: Session = Depends(get_db), _: models.User = Depends(require_management)):
    return analytics.by_faculty(db)


@router.get("/students")
def students(class_name: Optional[str] = None, subject_id: Optional[str] = None,
             db: Session = Depends(get_db), _: models.User = Depends(require_management)):
    return analytics.students_table(db, class_name=class_name, subject_id=subject_id)


@router.get("/students/{user_id}")
def student_detail(user_id: str, db: Session = Depends(get_db), _: models.User = Depends(require_management)):
    student = db.query(models.User).filter(
        models.User.id == user_id, models.User.role == models.RoleEnum.student
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return analytics.student_detail(db, student)
