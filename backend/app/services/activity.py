"""
Student activity tracking: logins, sessions and an append-only event log.

A *session* starts at login and is kept alive by the frontend's heartbeat
(every minute while a tab is open). If no heartbeat arrives for
SESSION_IDLE_MINUTES, the next heartbeat starts a new session — so
"sessions" and "time on platform" are measured, not guessed.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models

SESSION_IDLE_MINUTES = 30


def record_event(db: Session, user_id: str, event_type: str, detail: dict | None = None, commit: bool = True):
    db.add(models.ActivityEvent(user_id=user_id, event_type=event_type, detail=detail or {}))
    if commit:
        db.commit()


def _latest_session(db: Session, user_id: str) -> models.UserSession | None:
    return (
        db.query(models.UserSession)
        .filter(models.UserSession.user_id == user_id)
        .order_by(models.UserSession.last_seen_at.desc())
        .first()
    )


def start_session(db: Session, user: models.User) -> models.UserSession:
    now = datetime.utcnow()
    session = models.UserSession(user_id=user.id, started_at=now, last_seen_at=now)
    user.last_login_at = now
    db.add(session)
    db.add(user)
    record_event(db, user.id, "login", commit=False)
    db.commit()
    return session


def heartbeat(db: Session, user: models.User) -> models.UserSession:
    now = datetime.utcnow()
    session = _latest_session(db, user.id)
    if session and now - session.last_seen_at <= timedelta(minutes=SESSION_IDLE_MINUTES):
        session.last_seen_at = now
    else:
        session = models.UserSession(user_id=user.id, started_at=now, last_seen_at=now)
        record_event(db, user.id, "session_resumed", commit=False)
    db.add(session)
    db.commit()
    return session


def activity_summary(db: Session, user_id: str) -> dict:
    sessions = db.query(models.UserSession).filter(models.UserSession.user_id == user_id).all()
    logins = (
        db.query(models.ActivityEvent)
        .filter(models.ActivityEvent.user_id == user_id, models.ActivityEvent.event_type == "login")
        .count()
    )
    total_minutes = sum(
        max(1, int((s.last_seen_at - s.started_at).total_seconds() // 60)) for s in sessions
    )
    last_active = max((s.last_seen_at for s in sessions), default=None)
    return {
        "logins": logins,
        "sessions": len(sessions),
        "minutes_on_platform": total_minutes,
        "last_active": last_active,
    }
