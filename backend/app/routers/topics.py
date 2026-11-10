from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import get_current_user
from app.database import get_db
from app.services.access import accessible_topics_query

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("/", response_model=list[schemas.TopicOut])
def list_topics(
    document_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    q = accessible_topics_query(db, current_user)
    if document_id:
        q = q.filter(models.Topic.document_id == document_id)
    return q.all()
