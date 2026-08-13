from sqlalchemy.orm import Session

from app import models

MASTERY_THRESHOLD = 0.75


def generate_study_plan(db: Session, user_id: str) -> list[models.StudyPlanItem]:
    """
    Agentic study planner: looks at every topic across the student's uploaded
    documents, checks mastery scores, and (re)builds an ordered plan:
      1. Topics with no attempts yet, in document order.
      2. Topics below the mastery threshold ("needs_remediation") bubble up next.
      3. Mastered topics are marked complete and dropped from the active plan.
    This mirrors the doc's "autonomously decides the next best topic" behavior —
    re-running this after every quiz submission keeps the plan adaptive.
    """
    topics = (
        db.query(models.Topic)
        .join(models.Document)
        .filter(models.Document.user_id == user_id)
        .order_by(models.Topic.order_index)
        .all()
    )

    scores_by_topic = {
        s.topic_id: s
        for s in db.query(models.MasteryScore).filter(models.MasteryScore.user_id == user_id).all()
    }

    # Clear existing plan, rebuild fresh (simple & correct; fine at this scale).
    db.query(models.StudyPlanItem).filter(models.StudyPlanItem.user_id == user_id).delete()

    needs_remediation, not_started, mastered = [], [], []
    for topic in topics:
        score = scores_by_topic.get(topic.id)
        if score is None:
            not_started.append(topic)
        elif score.score < MASTERY_THRESHOLD:
            needs_remediation.append((topic, score))
        else:
            mastered.append(topic)

    plan_items: list[models.StudyPlanItem] = []
    order = 0

    for topic, score in needs_remediation:
        plan_items.append(
            models.StudyPlanItem(
                user_id=user_id,
                topic_id=topic.id,
                status="needs_remediation",
                scheduled_order=order,
                reason=f"Mastery {score.score:.0%} is below the {MASTERY_THRESHOLD:.0%} threshold.",
            )
        )
        order += 1

    for topic in not_started:
        plan_items.append(
            models.StudyPlanItem(
                user_id=user_id,
                topic_id=topic.id,
                status="pending",
                scheduled_order=order,
                reason="Not yet studied.",
            )
        )
        order += 1

    for topic in mastered:
        plan_items.append(
            models.StudyPlanItem(
                user_id=user_id,
                topic_id=topic.id,
                status="mastered",
                scheduled_order=order,
                reason="Mastery threshold met.",
            )
        )
        order += 1

    db.add_all(plan_items)
    db.commit()
    for item in plan_items:
        db.refresh(item)
    return plan_items
