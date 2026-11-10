from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.content_generator import generate_study_kit
from app.core.security import get_current_user
from app.database import get_db
from app.llm.factory import get_llm_provider
from app.services import gamification
from app.services.access import accessible_topics_query
from app.services.activity import record_event

router = APIRouter(prefix="/study-kit", tags=["study-kit"])


@router.post("/generate-advanced", response_model=schemas.StudyKitOut)
def generate(
    payload: schemas.StudyKitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    topic = accessible_topics_query(db, current_user).filter(models.Topic.id == payload.topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found in your subjects")

    if current_user.role == models.RoleEnum.student:
        # Self-assessment first: the pre-assessment score is the baseline that
        # improvement (and the improvement points) are measured against.
        has_pre = (
            db.query(models.QuizAttempt)
            .filter(
                models.QuizAttempt.user_id == current_user.id,
                models.QuizAttempt.topic_id == topic.id,
                models.QuizAttempt.score.isnot(None),
            )
            .first()
        )
        if not has_pre:
            raise HTTPException(
                status_code=409,
                detail="Take the quick pre-assessment for this topic first — it unlocks the study kit.",
            )

    llm = get_llm_provider()
    try:
        kit = generate_study_kit(db, llm, current_user.id, payload.topic_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if current_user.role == models.RoleEnum.student:
        gamification.on_study_kit_opened(db, current_user.id, topic.id, topic.title)
        record_event(db, current_user.id, "study_kit_opened", {"topic_id": topic.id, "topic": topic.title})
    return schemas.StudyKitOut(**kit)
