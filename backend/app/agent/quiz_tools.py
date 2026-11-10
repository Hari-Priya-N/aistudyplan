import json
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app import models
from app.llm.base import LLMProvider
from app.rag.vector_store import query_chunks

QUIZ_GEN_SYSTEM_PROMPT = """You are a quiz generator for an adaptive tutor. Given source material \
on a topic, write multiple-choice questions that test real understanding, not trivia recall.

Respond ONLY with JSON of this exact shape:
{
  "questions": [
    {"question": "string", "options": ["a", "b", "c", "d"], "correct_index": 0}
  ]
}
"""


def _get_topic_context(llm: LLMProvider, topic: models.Topic, query: str | None = None, top_k: int = 6) -> str:
    """Retrieve source chunks for a topic — searched only inside the topic's own document."""
    query = query or topic.title
    embedding = llm.embed([query])[0]
    results = query_chunks(embedding, document_ids=[topic.document_id], top_k=top_k)
    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else query


def next_quiz_kind(db: Session, user_id: str, topic_id: str) -> str:
    """1st submitted attempt on a topic = pre-assessment, 2nd = post-preparation, then practice."""
    done = (
        db.query(models.QuizAttempt)
        .filter(
            models.QuizAttempt.user_id == user_id,
            models.QuizAttempt.topic_id == topic_id,
            models.QuizAttempt.score.isnot(None),
        )
        .count()
    )
    if done == 0:
        return models.QuizKind.pre_assessment.value
    if done == 1:
        return models.QuizKind.post_preparation.value
    return models.QuizKind.practice.value


def generate_quiz(
    db: Session, llm: LLMProvider, user_id: str, topic_id: str, num_questions: int = 5
) -> models.QuizAttempt:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise ValueError("Topic not found")

    context = _get_topic_context(llm, topic)
    messages = [
        {"role": "system", "content": QUIZ_GEN_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Topic: {topic.title}\nDifficulty: {topic.difficulty}\n"
            f"Number of questions: {num_questions}\n\nSource material:\n{context[:6000]}",
        },
    ]
    raw = llm.complete(messages, temperature=0.4, max_tokens=1800, json_mode=True)
    try:
        parsed = json.loads(raw)
        questions = parsed.get("questions", [])[:num_questions]
    except json.JSONDecodeError:
        questions = []
    # Keep only well-formed questions so grading can never crash on bad LLM output.
    questions = [
        q for q in questions
        if isinstance(q, dict) and q.get("question") and isinstance(q.get("options"), list)
        and len(q["options"]) >= 2 and isinstance(q.get("correct_index"), int)
        and 0 <= q["correct_index"] < len(q["options"])
    ]
    if not questions:
        raise ValueError("The AI could not generate a quiz for this topic right now — please try again.")

    attempt = models.QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=user_id,
        topic_id=topic_id,
        kind=next_quiz_kind(db, user_id, topic_id),
        questions=questions,
        answers=None,
        score=None,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


EXPLAIN_SYSTEM_PROMPT = """You are a tutor explaining why a quiz answer was wrong. Be concise, \
specific, and encouraging. Explain the misconception the wrong answer suggests, then clarify the \
correct concept in 2-3 sentences."""


def evaluate_quiz(
    db: Session, llm: LLMProvider, attempt_id: str, answers: list[int], user_id: str | None = None
) -> dict:
    q = db.query(models.QuizAttempt).filter(models.QuizAttempt.id == attempt_id)
    if user_id:
        q = q.filter(models.QuizAttempt.user_id == user_id)
    attempt = q.first()
    if not attempt:
        raise ValueError("Quiz attempt not found")
    if attempt.score is not None:
        raise ValueError("This quiz was already submitted — start a new one to try again.")

    previous = (
        db.query(models.QuizAttempt)
        .filter(
            models.QuizAttempt.user_id == attempt.user_id,
            models.QuizAttempt.topic_id == attempt.topic_id,
            models.QuizAttempt.score.isnot(None),
        )
        .order_by(models.QuizAttempt.created_at.desc())
        .first()
    )
    previous_score = previous.score if previous else None

    questions = attempt.questions
    correct = 0
    explanations = []
    for i, q in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else None
        is_correct = user_answer == q.get("correct_index")
        if is_correct:
            correct += 1
        else:
            messages = [
                {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {q.get('question')}\n"
                        f"Options: {q.get('options')}\n"
                        f"Correct answer: {q.get('options', [''])[q.get('correct_index', 0)]}\n"
                        f"Student's answer: "
                        f"{q.get('options', [''])[user_answer] if user_answer is not None and user_answer < len(q.get('options', [])) else 'No answer'}"
                    ),
                },
            ]
            explanation = llm.complete(messages, temperature=0.3, max_tokens=250)
            explanations.append({"question_index": i, "explanation": explanation})

    score = correct / len(questions) if questions else 0.0

    attempt.answers = answers
    attempt.score = score
    attempt.explanations = explanations
    attempt.submitted_at = datetime.utcnow()
    db.add(attempt)

    # Update rolling mastery score for this topic (simple exponential update).
    mastery = (
        db.query(models.MasteryScore)
        .filter(
            models.MasteryScore.user_id == attempt.user_id,
            models.MasteryScore.topic_id == attempt.topic_id,
        )
        .first()
    )
    was_mastered = bool(mastery and mastery.score >= 0.75)
    if not mastery:
        mastery = models.MasteryScore(
            user_id=attempt.user_id, topic_id=attempt.topic_id, score=score, attempts=1
        )
    else:
        alpha = 0.5
        mastery.score = alpha * score + (1 - alpha) * mastery.score
        mastery.attempts += 1
    db.add(mastery)
    db.flush()

    # Motivation + activity tracking
    from app.services import gamification
    from app.services.activity import record_event

    topic_title = attempt.topic.title if attempt.topic else "topic"
    awards = gamification.on_quiz_submitted(
        db, attempt.user_id, attempt, previous_score,
        mastered_first_time=(not was_mastered and mastery.score >= 0.75), topic_title=topic_title,
    )
    record_event(db, attempt.user_id, "quiz_submitted",
                 {"topic_id": attempt.topic_id, "kind": attempt.kind, "score": score}, commit=False)
    db.commit()

    return {
        "score": score,
        "mastery_score": mastery.score,
        "explanations": explanations,
        "passed": score >= 0.75,
        "kind": attempt.kind,
        "previous_score": previous_score,
        "points_awarded": awards,
    }
