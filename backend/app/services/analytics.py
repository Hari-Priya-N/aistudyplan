"""
Metrics for the Management and Faculty dashboards.

Score journey per (student, topic)
----------------------------------
Every submitted quiz attempt on a topic is ordered by time:
  attempt 1 -> PRE-ASSESSMENT score     (before studying the topic)
  attempt 2 -> POST-PREPARATION score   ("initial test score post topic preparation")
  attempt 3+-> CONSECUTIVE scores
  improvement = latest score - pre-assessment score

Those per-topic journeys are then rolled up by student, class, subject,
faculty and elective. Focus areas = the student's topics whose latest score
is still below the mastery threshold, weakest first.
"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.agent.study_planner import MASTERY_THRESHOLD
from app.core.timeutil import local_date, utcnow


# ---------------------------------------------------------------- raw data
def _journeys(db: Session, student_ids: list[str] | None = None, subject_ids: list[str] | None = None):
    """Return {(user_id, topic_id): journey dict}."""
    q = (
        db.query(
            models.QuizAttempt.user_id,
            models.QuizAttempt.topic_id,
            models.QuizAttempt.kind,
            models.QuizAttempt.score,
            models.QuizAttempt.created_at,
            models.Topic.title,
            models.Document.subject_id,
        )
        .join(models.Topic, models.Topic.id == models.QuizAttempt.topic_id)
        .join(models.Document, models.Document.id == models.Topic.document_id)
        .filter(models.QuizAttempt.score.isnot(None))
    )
    if student_ids is not None:
        q = q.filter(models.QuizAttempt.user_id.in_(student_ids or ["__none__"]))
    if subject_ids is not None:
        q = q.filter(models.Document.subject_id.in_(subject_ids or ["__none__"]))

    grouped: dict[tuple, list] = defaultdict(list)
    meta: dict[tuple, dict] = {}
    for uid, tid, kind, score, created, title, subject_id in q.order_by(models.QuizAttempt.created_at):
        grouped[(uid, tid)].append({"score": score, "kind": kind, "at": created})
        meta[(uid, tid)] = {"topic_title": title, "subject_id": subject_id}

    journeys = {}
    for key, attempts in grouped.items():
        scores = [a["score"] for a in attempts]
        journeys[key] = {
            "user_id": key[0],
            "topic_id": key[1],
            **meta[key],
            "attempts": attempts,
            "pre": scores[0],
            "post": scores[1] if len(scores) > 1 else None,
            "consecutive": scores[2:],
            "latest": scores[-1],
            "improvement": (scores[-1] - scores[0]) if len(scores) > 1 else None,
        }
    return journeys


def _avg(values):
    vals = [v for v in values if v is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def _aggregate(journeys: list[dict]) -> dict:
    return {
        "pre_assessment_avg": _avg(j["pre"] for j in journeys),
        "post_preparation_avg": _avg(j["post"] for j in journeys),
        "latest_avg": _avg(j["latest"] for j in journeys),
        "improvement_avg": _avg(j["improvement"] for j in journeys),
        "topics_assessed": len(journeys),
        "quiz_attempts": sum(len(j["attempts"]) for j in journeys),
        "mastered_topics": sum(1 for j in journeys if j["latest"] >= MASTERY_THRESHOLD),
    }


def _focus_areas(journeys: list[dict], limit: int = 3) -> list[dict]:
    weak = sorted((j for j in journeys if j["latest"] < MASTERY_THRESHOLD), key=lambda j: j["latest"])
    return [{"topic_id": j["topic_id"], "topic_title": j["topic_title"], "latest": j["latest"]} for j in weak[:limit]]


def _activity_by_user(db: Session, user_ids: list[str]) -> dict[str, dict]:
    out = {uid: {"logins": 0, "sessions": 0, "minutes_on_platform": 0, "last_active": None} for uid in user_ids}
    if not user_ids:
        return out
    for uid, n in (
        db.query(models.ActivityEvent.user_id, func.count())
        .filter(models.ActivityEvent.user_id.in_(user_ids), models.ActivityEvent.event_type == "login")
        .group_by(models.ActivityEvent.user_id)
    ):
        out[uid]["logins"] = n
    for s in db.query(models.UserSession).filter(models.UserSession.user_id.in_(user_ids)):
        a = out[s.user_id]
        a["sessions"] += 1
        a["minutes_on_platform"] += max(1, int((s.last_seen_at - s.started_at).total_seconds() // 60))
        if not a["last_active"] or s.last_seen_at > a["last_active"]:
            a["last_active"] = s.last_seen_at
    return out


def _points_by_user(db: Session, user_ids: list[str]) -> dict[str, int]:
    if not user_ids:
        return {}
    return {
        uid: int(p)
        for uid, p in db.query(models.PointsTransaction.user_id, func.sum(models.PointsTransaction.points))
        .filter(models.PointsTransaction.user_id.in_(user_ids), models.PointsTransaction.points > 0)
        .group_by(models.PointsTransaction.user_id)
    }


def _students(db: Session, class_name: str | None = None, subject_id: str | None = None,
              subject_ids: list[str] | None = None) -> list[models.User]:
    q = db.query(models.User).filter(models.User.role == models.RoleEnum.student)
    if class_name:
        q = q.filter(models.User.class_name == class_name)
    scope = [subject_id] if subject_id else subject_ids
    if scope is not None:
        q = q.join(models.Enrollment, models.Enrollment.user_id == models.User.id).filter(
            models.Enrollment.subject_id.in_(scope or ["__none__"])
        ).distinct()
    return q.order_by(models.User.class_name, models.User.roll_no, models.User.email).all()


def _is_active(last_active: datetime | None, days: int = 7) -> bool:
    return bool(last_active and last_active >= utcnow() - timedelta(days=days))


# ---------------------------------------------------------------- management
def overview(db: Session) -> dict:
    students = _students(db)
    sids = [s.id for s in students]
    journeys = list(_journeys(db, sids).values())
    activity = _activity_by_user(db, sids)

    # Average score by attempt number (1 = pre-assessment, 2 = post-prep, 3+ = consecutive)
    by_attempt: dict[int, list[float]] = defaultdict(list)
    for j in journeys:
        for i, a in enumerate(j["attempts"][:6]):
            by_attempt[i + 1].append(a["score"])
    score_journey = [
        {"attempt": n, "label": {1: "Pre-assessment", 2: "Post-preparation"}.get(n, f"Attempt {n}"),
         "average": _avg(v), "count": len(v)}
        for n, v in sorted(by_attempt.items())
    ]

    # Daily active students, last 14 days
    since = utcnow() - timedelta(days=14)
    daily: dict = defaultdict(set)
    for s in db.query(models.UserSession).filter(
        models.UserSession.user_id.in_(sids or ["__none__"]), models.UserSession.last_seen_at >= since
    ):
        daily[local_date(s.started_at)].add(s.user_id)
    today = local_date(utcnow())
    daily_active = [
        {"date": (today - timedelta(days=d)).isoformat(), "active_students": len(daily.get(today - timedelta(days=d), ()))}
        for d in range(13, -1, -1)
    ]

    return {
        "counts": {
            "students": len(students),
            "faculty": db.query(models.User).filter(models.User.role == models.RoleEnum.instructor).count(),
            "classes": len({s.class_name for s in students if s.class_name}),
            "subjects": db.query(models.Subject).filter(models.Subject.is_elective.is_(False)).count(),
            "electives": db.query(models.Subject).filter(models.Subject.is_elective.is_(True)).count(),
            "active_students_7d": sum(1 for a in activity.values() if _is_active(a["last_active"])),
            "total_logins": sum(a["logins"] for a in activity.values()),
        },
        "scores": _aggregate(journeys),
        "score_journey": score_journey,
        "daily_active": daily_active,
    }


def by_class(db: Session) -> list[dict]:
    students = _students(db)
    journeys = _journeys(db, [s.id for s in students])
    activity = _activity_by_user(db, [s.id for s in students])
    classes: dict[str, list] = defaultdict(list)
    for s in students:
        classes[s.class_name or "Unassigned"].append(s)
    rows = []
    for cname, members in sorted(classes.items()):
        ids = {m.id for m in members}
        js = [j for (uid, _), j in journeys.items() if uid in ids]
        rows.append({
            "class_name": cname,
            "students": len(members),
            "active_students_7d": sum(1 for m in members if _is_active(activity[m.id]["last_active"])),
            "avg_logins": round(sum(activity[m.id]["logins"] for m in members) / len(members), 1),
            **_aggregate(js),
        })
    return rows


def _subject_row(db: Session, subject: models.Subject, journeys: dict) -> dict:
    js = [j for j in journeys.values() if j["subject_id"] == subject.id]
    topic_scores: dict[str, list] = defaultdict(list)
    for j in js:
        topic_scores[j["topic_title"]].append(j["latest"])
    weakest = sorted(((t, _avg(v)) for t, v in topic_scores.items()), key=lambda x: x[1])[:3]
    return {
        "subject_id": subject.id,
        "code": subject.code,
        "name": subject.name,
        "is_elective": bool(subject.is_elective),
        "faculty": subject.faculty.display_name if subject.faculty else None,
        "enrolled": len(subject.enrollments),
        "content_items": len(subject.documents),
        "weakest_topics": [{"topic_title": t, "latest_avg": a} for t, a in weakest],
        **_aggregate(js),
    }


def by_subject(db: Session, elective: bool | None = None) -> list[dict]:
    q = db.query(models.Subject)
    if elective is not None:
        q = q.filter(models.Subject.is_elective.is_(elective))
    subjects = q.order_by(models.Subject.is_elective, models.Subject.code).all()
    journeys = _journeys(db, subject_ids=[s.id for s in subjects])
    return [_subject_row(db, s, journeys) for s in subjects]


def by_faculty(db: Session) -> list[dict]:
    faculty = db.query(models.User).filter(models.User.role == models.RoleEnum.instructor).all()
    journeys = _journeys(db)
    rows = []
    for f in faculty:
        subjects = db.query(models.Subject).filter(models.Subject.faculty_id == f.id).all()
        sub_ids = {s.id for s in subjects}
        js = [j for j in journeys.values() if j["subject_id"] in sub_ids]
        reached = {
            e.user_id for e in db.query(models.Enrollment).filter(models.Enrollment.subject_id.in_(sub_ids or ["__none__"]))
        }
        rows.append({
            "faculty_id": f.id,
            "name": f.display_name,
            "email": f.email,
            "subjects": [f"{s.code} · {s.name}" for s in subjects],
            "students_reached": len(reached),
            "content_uploaded": db.query(models.Document).filter(models.Document.user_id == f.id).count(),
            "last_active": _activity_by_user(db, [f.id])[f.id]["last_active"],
            **_aggregate(js),
        })
    return rows


def students_table(db: Session, class_name: str | None = None, subject_id: str | None = None,
                   subject_ids: list[str] | None = None, limited: bool = False) -> list[dict]:
    """
    One row per student. `limited=True` is the Faculty version: scores are
    restricted to the faculty's own subjects, and engagement detail (time on
    platform, points) is left out.
    """
    students = _students(db, class_name, subject_id, subject_ids)
    sids = [s.id for s in students]
    scope = [subject_id] if subject_id else subject_ids
    journeys = _journeys(db, sids, scope)
    activity = _activity_by_user(db, sids)
    points = {} if limited else _points_by_user(db, sids)
    by_student: dict[str, list] = defaultdict(list)
    for (uid, _), j in journeys.items():
        by_student[uid].append(j)

    rows = []
    for s in students:
        js = by_student.get(s.id, [])
        a = activity[s.id]
        row = {
            "user_id": s.id,
            "name": s.display_name,
            "email": s.email,
            "roll_no": s.roll_no,
            "class_name": s.class_name,
            "logins": a["logins"],
            "last_active": a["last_active"],
            "focus_areas": _focus_areas(js),
            **_aggregate(js),
        }
        if not limited:
            row.update({
                "sessions": a["sessions"],
                "minutes_on_platform": a["minutes_on_platform"],
                "points": points.get(s.id, 0),
                "electives": [e.subject.name for e in s.enrollments if e.subject and e.subject.is_elective],
            })
        rows.append(row)
    return rows


def student_detail(db: Session, student: models.User, subject_ids: list[str] | None = None) -> dict:
    journeys = sorted(
        _journeys(db, [student.id], subject_ids).values(), key=lambda j: (j["subject_id"] or "", j["topic_title"])
    )
    subjects = {s.id: s for s in db.query(models.Subject)}
    events = (
        db.query(models.ActivityEvent)
        .filter(models.ActivityEvent.user_id == student.id)
        .order_by(models.ActivityEvent.created_at.desc())
        .limit(30)
        .all()
    )
    since = utcnow() - timedelta(days=14)
    minutes_by_day: dict = defaultdict(int)
    for s in db.query(models.UserSession).filter(
        models.UserSession.user_id == student.id, models.UserSession.last_seen_at >= since
    ):
        minutes_by_day[local_date(s.started_at)] += max(1, int((s.last_seen_at - s.started_at).total_seconds() // 60))
    today = local_date(utcnow())
    return {
        "student": {
            "user_id": student.id,
            "name": student.display_name,
            "email": student.email,
            "roll_no": student.roll_no,
            "class_name": student.class_name,
            "subjects": [
                {"code": e.subject.code, "name": e.subject.name, "is_elective": bool(e.subject.is_elective)}
                for e in student.enrollments if e.subject
            ],
        },
        "activity": _activity_by_user(db, [student.id])[student.id],
        "scores": _aggregate(journeys),
        "focus_areas": _focus_areas(journeys, limit=5),
        "topics": [
            {
                "topic_id": j["topic_id"],
                "topic_title": j["topic_title"],
                "subject": subjects[j["subject_id"]].name if j["subject_id"] in subjects else None,
                "pre": j["pre"],
                "post": j["post"],
                "consecutive": j["consecutive"],
                "latest": j["latest"],
                "improvement": j["improvement"],
                "attempts": [{"score": a["score"], "kind": a["kind"], "at": a["at"]} for a in j["attempts"]],
            }
            for j in journeys
        ],
        "daily_minutes": [
            {"date": (today - timedelta(days=d)).isoformat(), "minutes": minutes_by_day.get(today - timedelta(days=d), 0)}
            for d in range(13, -1, -1)
        ],
        "recent_events": [
            {"event_type": e.event_type, "detail": e.detail, "created_at": e.created_at} for e in events
        ],
    }
