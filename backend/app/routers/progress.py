from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/trends", response_model=schemas.ProgressOut)
def trends(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    scores = (
        db.query(models.MasteryScore).filter(models.MasteryScore.user_id == current_user.id).all()
    )
    trend_list = [
        schemas.ProgressTrend(
            topic_id=s.topic_id,
            topic_title=s.topic.title if s.topic else "Unknown",
            score=s.score,
            attempts=s.attempts,
            status="mastered" if s.score >= 0.75 else "needs_remediation",
        )
        for s in scores
    ]
    overall = sum(s.score for s in scores) / len(scores) if scores else 0.0
    return schemas.ProgressOut(overall_mastery=overall, trends=trend_list)


@router.get("/cohort")
def cohort_dashboard(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Instructor-only: per-topic mastery aggregated across all students."""
    from fastapi import HTTPException

    if current_user.role not in (models.RoleEnum.instructor, models.RoleEnum.management):
        raise HTTPException(status_code=403, detail="Instructor role required")

    from app.services.access import subject_ids_for_user

    subject_ids = subject_ids_for_user(db, current_user)
    q = db.query(models.MasteryScore)
    if subject_ids is not None:
        q = (
            q.join(models.Topic, models.Topic.id == models.MasteryScore.topic_id)
            .join(models.Document, models.Document.id == models.Topic.document_id)
            .filter(models.Document.subject_id.in_(subject_ids or ["__none__"]))
        )
    scores = q.all()
    by_topic: dict[str, list[float]] = {}
    titles: dict[str, str] = {}
    for s in scores:
        by_topic.setdefault(s.topic_id, []).append(s.score)
        if s.topic:
            titles[s.topic_id] = s.topic.title

    return [
        {
            "topic_id": tid,
            "topic_title": titles.get(tid, "Unknown"),
            "average_mastery": sum(vals) / len(vals),
            "student_count": len(vals),
        }
        for tid, vals in by_topic.items()
    ]
