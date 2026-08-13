import json
import uuid

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


def _get_topic_context(llm: LLMProvider, user_id: str, topic_title: str, top_k: int = 6) -> str:
    embedding = llm.embed([topic_title])[0]
    results = query_chunks(embedding, user_id=user_id, top_k=top_k)
    docs = results.get("documents", [[]])[0]
    return "\n\n".join(docs) if docs else topic_title


def generate_quiz(
    db: Session, llm: LLMProvider, user_id: str, topic_id: str, num_questions: int = 5
) -> models.QuizAttempt:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        raise ValueError("Topic not found")

    context = _get_topic_context(llm, user_id, topic.title)
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

    attempt = models.QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=user_id,
        topic_id=topic_id,
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
    db: Session, llm: LLMProvider, attempt_id: str, answers: list[int]
) -> dict:
    attempt = db.query(models.QuizAttempt).filter(models.QuizAttempt.id == attempt_id).first()
    if not attempt:
        raise ValueError("Quiz attempt not found")

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
    if not mastery:
        mastery = models.MasteryScore(
            user_id=attempt.user_id, topic_id=attempt.topic_id, score=score, attempts=1
        )
    else:
        alpha = 0.5
        mastery.score = alpha * score + (1 - alpha) * mastery.score
        mastery.attempts += 1
    db.add(mastery)
    db.commit()

    return {
        "score": score,
        "mastery_score": mastery.score,
        "explanations": explanations,
        "passed": score >= 0.75,
    }
