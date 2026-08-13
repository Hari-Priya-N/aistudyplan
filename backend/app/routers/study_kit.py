from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.content_generator import generate_study_kit
from app.core.security import get_current_user
from app.database import get_db
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/study-kit", tags=["study-kit"])


@router.post("/generate-advanced", response_model=schemas.StudyKitOut)
def generate(
    payload: schemas.StudyKitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    llm = get_llm_provider()
    try:
        kit = generate_study_kit(db, llm, current_user.id, payload.topic_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return schemas.StudyKitOut(**kit)
