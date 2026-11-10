"""
Faculty view — dashboard with *limited* metrics at each student level,
restricted to the subjects that faculty member teaches.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.core.security import require_staff
from app.database import get_db
from app.services import analytics
from app.services.access import subject_ids_for_user

router = APIRouter(prefix="/faculty-dashboard", tags=["faculty"])


@router.get("/students")
def my_students(subject_id: Optional[str] = None, db: Session = Depends(get_db),
                current_user: models.User = Depends(require_staff)):
    scope = subject_ids_for_user(db, current_user)   # None for management = all
    if subject_id and scope is not None and subject_id not in scope:
        raise HTTPException(status_code=403, detail="Not one of your subjects")
    return analytics.students_table(db, subject_id=subject_id, subject_ids=scope, limited=True)


@router.get("/subjects")
def my_subjects(db: Session = Depends(get_db), current_user: models.User = Depends(require_staff)):
    scope = subject_ids_for_user(db, current_user)
    subjects = db.query(models.Subject)
    if scope is not None:
        subjects = subjects.filter(models.Subject.id.in_(scope or ["__none__"]))
    subjects = subjects.all()
    journeys = analytics._journeys(db, subject_ids=[s.id for s in subjects])
    return [analytics._subject_row(db, s, journeys) for s in subjects]


@router.get("/students/{user_id}")
def student_detail(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(require_staff)):
    scope = subject_ids_for_user(db, current_user)
    student = db.query(models.User).filter(models.User.id == user_id, models.User.role == models.RoleEnum.student).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if scope is not None:
        enrolled = {e.subject_id for e in student.enrollments}
        if not enrolled & set(scope):
            raise HTTPException(status_code=403, detail="This student isn't in your subjects")
    detail = analytics.student_detail(db, student, subject_ids=scope)
    # limited view: drop the raw activity log
    detail.pop("recent_events", None)
    return detail
