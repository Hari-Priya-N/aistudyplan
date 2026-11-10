"""
Motivation layer: credit points, levels, badges, streaks, leaderboard, and the
daily Elara chat quota (which points can extend).

Why students want to self-assess
--------------------------------
* The pre-assessment is the single biggest point award, and the study kit for
  a topic unlocks only after it — so self-assessing is the way *in*.
* Improvement is rewarded more than raw score: +1 point per percentage point
  gained over your previous attempt, so weaker students can out-earn stronger
  ones by improving.
* Points are spendable: redeem them for extra Elara (AI tutor) messages
  beyond the daily quota.
* Class leaderboard + badges + daily streak give a social / habit hook.

All numbers live in POINT_RULES so faculty/management can tune them.
"""
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.core.config import get_settings
from app.core.timeutil import local_date, local_day_start_utc, utcnow

POINT_RULES = {
    "daily_login": 2,
    "streak_bonus": 3,            # extra per day once the streak is >= 3 days
    "pre_assessment": 10,
    "quiz_completed": 5,
    "improvement_per_pct": 1,     # per percentage point over previous attempt
    "improvement_cap": 30,
    "topic_mastered": 25,         # first time a topic crosses the mastery threshold
    "study_kit_opened": 1,        # first time per topic
}
POINTS_PER_LEVEL = 100


def award(db: Session, user_id: str, points: int, reason: str, description: str, commit: bool = False):
    if points == 0:
        return None
    tx = models.PointsTransaction(user_id=user_id, points=points, reason=reason, description=description)
    db.add(tx)
    if commit:
        db.commit()
    return {"points": points, "reason": reason, "description": description}


def _awarded_today(db: Session, user_id: str, reason: str) -> bool:
    return (
        db.query(models.PointsTransaction)
        .filter(
            models.PointsTransaction.user_id == user_id,
            models.PointsTransaction.reason == reason,
            models.PointsTransaction.created_at >= local_day_start_utc(),
        )
        .first()
        is not None
    )


# ------------------------------------------------------------------ streaks
def active_dates(db: Session, user_id: str) -> set:
    rows = (
        db.query(models.UserSession.started_at, models.UserSession.last_seen_at)
        .filter(models.UserSession.user_id == user_id)
        .all()
    )
    dates = set()
    for started, last_seen in rows:
        dates.add(local_date(started))
        dates.add(local_date(last_seen))
    return dates


def current_streak(db: Session, user_id: str) -> int:
    dates = active_dates(db, user_id)
    if not dates:
        return 0
    day = local_date(utcnow())
    if day not in dates:
        day = day - timedelta(days=1)   # streak still alive if you were active yesterday
    streak = 0
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


# ------------------------------------------------------------------ hooks
def on_login(db: Session, user: models.User) -> list[dict]:
    if user.role != models.RoleEnum.student:
        return []
    awards = []
    if not _awarded_today(db, user.id, "daily_login"):
        awards.append(award(db, user.id, POINT_RULES["daily_login"], "daily_login", "Daily check-in"))
        streak = current_streak(db, user.id)
        if streak >= 3:
            awards.append(
                award(db, user.id, POINT_RULES["streak_bonus"], "streak_bonus", f"{streak}-day learning streak")
            )
    db.commit()
    return [a for a in awards if a]


def on_quiz_submitted(
    db: Session,
    user_id: str,
    attempt: models.QuizAttempt,
    previous_score: float | None,
    mastered_first_time: bool,
    topic_title: str,
) -> list[dict]:
    awards = []
    if attempt.kind == models.QuizKind.pre_assessment.value:
        awards.append(award(db, user_id, POINT_RULES["pre_assessment"], "pre_assessment",
                            f"Self-assessment: {topic_title}"))
    else:
        awards.append(award(db, user_id, POINT_RULES["quiz_completed"], "quiz_completed",
                            f"Quiz completed: {topic_title}"))
    if previous_score is not None and attempt.score is not None and attempt.score > previous_score:
        gained = round((attempt.score - previous_score) * 100)
        pts = min(POINT_RULES["improvement_cap"], gained * POINT_RULES["improvement_per_pct"])
        awards.append(award(db, user_id, pts, "improvement", f"Improved {gained}% on {topic_title}"))
    if mastered_first_time:
        awards.append(award(db, user_id, POINT_RULES["topic_mastered"], "topic_mastered",
                            f"Mastered {topic_title}"))
    return [a for a in awards if a]


def on_study_kit_opened(db: Session, user_id: str, topic_id: str, topic_title: str):
    already = (
        db.query(models.ActivityEvent)
        .filter(
            models.ActivityEvent.user_id == user_id,
            models.ActivityEvent.event_type == "study_kit_opened",
        )
        .all()
    )
    if any((e.detail or {}).get("topic_id") == topic_id for e in already):
        return None
    return award(db, user_id, POINT_RULES["study_kit_opened"], "study_kit_opened",
                 f"Started studying {topic_title}")


# ------------------------------------------------------------------ read models
def balance(db: Session, user_id: str) -> int:
    return int(
        db.query(func.coalesce(func.sum(models.PointsTransaction.points), 0))
        .filter(models.PointsTransaction.user_id == user_id)
        .scalar()
        or 0
    )


def lifetime_earned(db: Session, user_id: str) -> int:
    return int(
        db.query(func.coalesce(func.sum(models.PointsTransaction.points), 0))
        .filter(models.PointsTransaction.user_id == user_id, models.PointsTransaction.points > 0)
        .scalar()
        or 0
    )


def badges(db: Session, user_id: str) -> list[dict]:
    reasons = {
        r for (r,) in db.query(models.PointsTransaction.reason)
        .filter(models.PointsTransaction.user_id == user_id).distinct()
    }
    improvements = [
        t.description for t in db.query(models.PointsTransaction)
        .filter(models.PointsTransaction.user_id == user_id, models.PointsTransaction.reason == "improvement")
    ]
    big_jump = (
        db.query(models.PointsTransaction)
        .filter(
            models.PointsTransaction.user_id == user_id,
            models.PointsTransaction.reason == "improvement",
            models.PointsTransaction.points >= 20,
        )
        .first()
        is not None
    )
    mastered = (
        db.query(models.PointsTransaction)
        .filter(models.PointsTransaction.user_id == user_id, models.PointsTransaction.reason == "topic_mastered")
        .count()
    )
    sessions = db.query(models.UserSession).filter(models.UserSession.user_id == user_id).count()
    streak = current_streak(db, user_id)
    defs = [
        ("first_step", "First Step", "Complete your first pre-assessment", "pre_assessment" in reasons),
        ("improver", "Improver", "Improve on any topic", bool(improvements)),
        ("big_leap", "Big Leap", "Improve a topic by 20% or more in one go", big_jump),
        ("topic_master", "Topic Master", "Master your first topic", mastered >= 1),
        ("scholar", "Scholar", "Master 5 topics", mastered >= 5),
        ("regular", "Regular", "Use the platform in 5 separate sessions", sessions >= 5),
        ("on_fire", "On Fire", "Keep a 3-day learning streak", streak >= 3),
    ]
    return [{"id": i, "name": n, "description": d, "earned": bool(e)} for i, n, d, e in defs]


def leaderboard(db: Session, class_name: str | None, limit: int = 10) -> list[dict]:
    q = (
        db.query(models.User, func.coalesce(func.sum(models.PointsTransaction.points), 0).label("pts"))
        .outerjoin(
            models.PointsTransaction,
            (models.PointsTransaction.user_id == models.User.id) & (models.PointsTransaction.points > 0),
        )
        .filter(models.User.role == models.RoleEnum.student)
        .group_by(models.User.id)
    )
    if class_name:
        q = q.filter(models.User.class_name == class_name)
    rows = q.order_by(func.coalesce(func.sum(models.PointsTransaction.points), 0).desc()).all()
    return [
        {"rank": i + 1, "user_id": u.id, "name": u.display_name, "points": int(p)}
        for i, (u, p) in enumerate(rows[:limit])
    ] if rows else []


def rank_in_class(db: Session, user: models.User) -> dict:
    board = leaderboard(db, user.class_name, limit=10_000)
    for row in board:
        if row["user_id"] == user.id:
            return {"rank": row["rank"], "of": len(board)}
    return {"rank": None, "of": len(board)}


# ------------------------------------------------------------------ Elara chat quota
def chat_quota(db: Session, user: models.User) -> dict:
    settings = get_settings()
    if user.role != models.RoleEnum.student:
        return {"limited": False, "limit": None, "used": 0, "remaining": None, "bonus": 0}
    since = local_day_start_utc()
    used = (
        db.query(models.ChatMessage)
        .filter(
            models.ChatMessage.user_id == user.id,
            models.ChatMessage.role == "user",
            models.ChatMessage.created_at >= since,
        )
        .count()
    )
    redemptions = (
        db.query(models.PointsTransaction)
        .filter(
            models.PointsTransaction.user_id == user.id,
            models.PointsTransaction.reason == "redeem_chat",
            models.PointsTransaction.created_at >= since,
        )
        .count()
    )
    bonus = redemptions * settings.redeem_bonus_messages
    limit = settings.chat_daily_quota + bonus
    return {
        "limited": True,
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "bonus": bonus,
        "redeem_cost": settings.redeem_cost_points,
        "redeem_bonus": settings.redeem_bonus_messages,
    }


def redeem_chat_messages(db: Session, user: models.User) -> dict:
    settings = get_settings()
    if balance(db, user.id) < settings.redeem_cost_points:
        raise ValueError(f"You need {settings.redeem_cost_points} points to unlock more messages.")
    award(db, user.id, -settings.redeem_cost_points, "redeem_chat",
          f"Unlocked {settings.redeem_bonus_messages} extra Elara messages", commit=True)
    return chat_quota(db, user)


def summary(db: Session, user: models.User) -> dict:
    earned = lifetime_earned(db, user.id)
    level = earned // POINTS_PER_LEVEL + 1
    history = (
        db.query(models.PointsTransaction)
        .filter(models.PointsTransaction.user_id == user.id)
        .order_by(models.PointsTransaction.created_at.desc())
        .limit(15)
        .all()
    )
    return {
        "balance": balance(db, user.id),
        "lifetime_earned": earned,
        "level": level,
        "level_progress": (earned % POINTS_PER_LEVEL) / POINTS_PER_LEVEL,
        "points_to_next_level": POINTS_PER_LEVEL - earned % POINTS_PER_LEVEL,
        "streak_days": current_streak(db, user.id),
        "badges": badges(db, user.id),
        "class_rank": rank_in_class(db, user),
        "leaderboard": leaderboard(db, user.class_name),
        "class_name": user.class_name,
        "rules": POINT_RULES,
        "history": [
            {"points": t.points, "description": t.description, "created_at": t.created_at} for t in history
        ],
        "chat_quota": chat_quota(db, user),
    }
