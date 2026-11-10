from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.study_planner import generate_study_plan
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


def _to_out(db: Session, user_id: str, items) -> list[schemas.StudyPlanItemOut]:
    assessed = {
        tid for (tid,) in db.query(models.QuizAttempt.topic_id)
        .filter(models.QuizAttempt.user_id == user_id, models.QuizAttempt.score.isnot(None))
        .distinct()
    }
    out = []
    for i in items:
        subject = i.topic.document.subject if i.topic and i.topic.document else None
        out.append(
            schemas.StudyPlanItemOut(
                id=i.id,
                topic_id=i.topic_id,
                topic_title=i.topic.title,
                subject_name=subject.name if subject else "My uploads",
                is_elective=bool(subject and subject.is_elective),
                has_pre_assessment=i.topic_id in assessed,
                status=i.status,
                scheduled_order=i.scheduled_order,
                reason=i.reason,
            )
        )
    return out


@router.post("/generate", response_model=list[schemas.StudyPlanItemOut])
def generate(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """(Re)build the adaptive plan over every topic in the student's subjects."""
    items = generate_study_plan(db, current_user.id)
    return _to_out(db, current_user.id, items)


@router.get("/", response_model=list[schemas.StudyPlanItemOut])
def get_plan(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    items = (
        db.query(models.StudyPlanItem)
        .filter(models.StudyPlanItem.user_id == current_user.id)
        .order_by(models.StudyPlanItem.scheduled_order)
        .all()
    )
    return _to_out(db, current_user.id, items)
