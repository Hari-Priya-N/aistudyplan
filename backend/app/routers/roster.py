"""Excel/CSV student registration (Faculty + Management)."""
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import models
from app.core.security import require_staff
from app.database import get_db
from app.services.activity import record_event
from app.services.roster import import_roster, template_workbook

router = APIRouter(prefix="/roster", tags=["roster"])

MAX_BYTES = 5 * 1024 * 1024


@router.get("/template")
def download_template(current_user: models.User = Depends(require_staff)):
    return Response(
        content=template_workbook(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student_roster_template.xlsx"'},
    )


@router.post("/upload")
async def upload_roster(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_staff),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".xlsx", ".csv"}:
        raise HTTPException(status_code=400, detail="Upload an Excel (.xlsx) or CSV file")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is larger than 5 MB")
    try:
        result = import_roster(db, file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read that file — use the template's column layout")
    record_event(db, current_user.id, "roster_uploaded",
                 {"created": result["students_created"], "updated": result["students_updated"]})
    return result


@router.get("/students")
def list_registered_students(
    db: Session = Depends(get_db), current_user: models.User = Depends(require_staff)
):
    """Students registered in the faculty member's subjects (all students for management)."""
    q = db.query(models.User).filter(models.User.role == models.RoleEnum.student)
    if current_user.role == models.RoleEnum.instructor:
        sub_ids = [s.id for s in db.query(models.Subject).filter(
            (models.Subject.faculty_id == current_user.id) | (models.Subject.faculty_id.is_(None)))]
        q = q.join(models.Enrollment).filter(models.Enrollment.subject_id.in_(sub_ids or ["__none__"])).distinct()
    return [
        {
            "id": u.id, "name": u.display_name, "email": u.email, "roll_no": u.roll_no,
            "class_name": u.class_name,
            "subjects": [e.subject.code for e in u.enrollments if e.subject],
            "first_login_done": u.last_login_at is not None,
        }
        for u in q.order_by(models.User.class_name, models.User.roll_no).all()
    ]
