from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.quiz_tools import generate_quiz, evaluate_quiz
from app.agent.study_planner import MASTERY_THRESHOLD
from app.core.security import get_current_user
from app.database import get_db
from app.llm.factory import get_llm_provider
from app.services.access import accessible_topics_query

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=schemas.QuizOut)
def generate(
    payload: schemas.QuizGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not accessible_topics_query(db, current_user).filter(models.Topic.id == payload.topic_id).first():
        raise HTTPException(status_code=404, detail="Topic not found in your subjects")
    llm = get_llm_provider()
    try:
        attempt = generate_quiz(db, llm, current_user.id, payload.topic_id, payload.num_questions)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Never send correct_index to the client before submission.
    sanitized = [{"question": q["question"], "options": q["options"]} for q in attempt.questions]
    return schemas.QuizOut(quiz_id=attempt.id, topic_id=attempt.topic_id, kind=attempt.kind, questions=sanitized)


@router.post("/submit", response_model=schemas.QuizResultOut)
def submit(
    payload: schemas.QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    llm = get_llm_provider()
    try:
        result = evaluate_quiz(db, llm, payload.quiz_id, payload.answers, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Score gating: below threshold -> flag that remediation should run before
    # the student can advance. The frontend calls /remediation/micro-module next.
    remediation_triggered = result["mastery_score"] < MASTERY_THRESHOLD

    return schemas.QuizResultOut(
        quiz_id=payload.quiz_id,
        score=result["score"],
        mastery_score=result["mastery_score"],
        passed=result["passed"],
        explanations=result["explanations"],
        remediation_triggered=remediation_triggered,
        kind=result["kind"],
        previous_score=result["previous_score"],
        points_awarded=result["points_awarded"],
    )


@router.get("/{quiz_id}/explain-answer/{question_index}")
def explain_answer(
    quiz_id: str,
    question_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns the stored explanation for a specific incorrect answer (generated at submit time)."""
    attempt = (
        db.query(models.QuizAttempt)
        .filter(models.QuizAttempt.id == quiz_id, models.QuizAttempt.user_id == current_user.id)
        .first()
    )
    if not attempt or attempt.explanations is None:
        raise HTTPException(status_code=404, detail="No explanation available for this quiz yet")

    match = next((e for e in attempt.explanations if e["question_index"] == question_index), None)
    if not match:
        return {"question_index": question_index, "explanation": "That answer was correct — no explanation needed."}
    return match
