from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.study_planner import generate_study_plan
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/study-plan", tags=["study-plan"])


@router.post("/generate", response_model=list[schemas.StudyPlanItemOut])
def generate(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    items = generate_study_plan(db, current_user.id)
    return [
        schemas.StudyPlanItemOut(
            id=i.id,
            topic_id=i.topic_id,
            topic_title=i.topic.title,
            status=i.status,
            scheduled_order=i.scheduled_order,
            reason=i.reason,
        )
        for i in items
    ]


@router.get("/", response_model=list[schemas.StudyPlanItemOut])
def get_plan(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    items = (
        db.query(models.StudyPlanItem)
        .filter(models.StudyPlanItem.user_id == current_user.id)
        .order_by(models.StudyPlanItem.scheduled_order)
        .all()
    )
    return [
        schemas.StudyPlanItemOut(
            id=i.id,
            topic_id=i.topic_id,
            topic_title=i.topic.title,
            status=i.status,
            scheduled_order=i.scheduled_order,
            reason=i.reason,
        )
        for i in items
    ]
