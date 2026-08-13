from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import get_current_user
from app.database import get_db

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/", response_model=list[schemas.TopicOut])
def list_topics(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    topics = (
        db.query(models.Topic)
        .join(models.Document)
        .filter(models.Document.user_id == current_user.id)
        .order_by(models.Topic.order_index)
        .all()
    )
    return topics
