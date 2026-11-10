"""Student-facing activity + motivation endpoints ("visible to the student in his view")."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.core.security import get_current_user
from app.database import get_db
from app.services import analytics, gamification
from app.services.activity import heartbeat

router = APIRouter(tags=["activity & rewards"])


@router.post("/activity/heartbeat")
def ping(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Called by the web app every minute while open — measures sessions and time on platform."""
    session = heartbeat(db, current_user)
    return {"session_id": session.id, "started_at": session.started_at}


@router.get("/activity/me")
def my_activity(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Logins, sessions, minutes, score journey per topic and improvement — for the student."""
    return analytics.student_detail(db, current_user)


@router.get("/rewards/me")
def my_rewards(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return gamification.summary(db, current_user)
