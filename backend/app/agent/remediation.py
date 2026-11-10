from sqlalchemy.orm import Session

from app import models
from app.agent.quiz_tools import _get_topic_context
from app.agent.study_planner import MASTERY_THRESHOLD
from app.llm.base import LLMProvider

MICRO_MODULE_SYSTEM_PROMPT = """You are a remediation tutor. The student struggled with a specific \
sub-concept. Write a short, focused micro-learning module (3-5 short paragraphs) that re-teaches \
JUST that sub-concept clearly, with a simple example. Do not re-teach the whole topic."""


def analyze_knowledge_gaps(db: Session, user_id: str) -> list[dict]:
    """
    Knowledge-gap dashboard data: every topic below the mastery threshold,
    with the gap size, for per-topic mastery visualization.
    """
    scores = (
        db.query(models.MasteryScore)
        .filter(models.MasteryScore.user_id == user_id)
        .all()
    )
    gaps = []
    for s in scores:
        if s.score < MASTERY_THRESHOLD:
            gaps.append(
                {
                    "topic_id": s.topic_id,
                    "topic_title": s.topic.title if s.topic else "Unknown",
                    "score": s.score,
                    "gap": round(MASTERY_THRESHOLD - s.score, 2),
                    "attempts": s.attempts,
                }
            )
    return sorted(gaps, key=lambda g: -g["gap"])


def generate_remediation(
    db: Session, llm: LLMProvider, user_id: str, topic_id: str, sub_concept: str | None = None
) -> dict:
    """
    Score-gating: this is called whenever a quiz score falls below the mastery
    threshold. It produces a targeted micro-module rather than making the
    student re-study the whole topic, and the caller (quiz submit endpoint)
    is responsible for NOT advancing the student in the study plan until a
    follow-up attempt clears the threshold.
    """
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise ValueError("Topic not found")

    focus = sub_concept or topic.title
    context = _get_topic_context(llm, topic, query=focus)

    messages = [
        {"role": "system", "content": MICRO_MODULE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Topic: {topic.title}\nStruggling sub-concept: {focus}\n\n"
            f"Reference material:\n{context[:4000]}",
        },
    ]
    micro_module = llm.complete(messages, temperature=0.3, max_tokens=700)

    return {
        "topic_id": topic_id,
        "micro_module": micro_module,
        "explanation": f"This micro-module targets '{focus}' specifically, based on your recent quiz performance.",
        "resources": [],  # populated by resource_finder for chat-triggered remediation
    }
