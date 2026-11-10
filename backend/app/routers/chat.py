from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.graph import run_tutor_agent
from app.core.cache import append_session_message
from app.core.security import decode_token, get_current_user
from app.database import get_db, SessionLocal
from app.llm.factory import get_llm_provider
from app.services import gamification
from app.services.activity import record_event

router = APIRouter(prefix="/chat", tags=["chat"])


def _check_quota(db: Session, user: models.User) -> None:
    """Elara is rate-limited per student per day (CHAT_DAILY_QUOTA); points can buy more."""
    quota = gamification.chat_quota(db, user)
    if quota["limited"] and quota["remaining"] <= 0:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've used all {quota['limit']} Elara messages for today. "
                f"Spend {quota['redeem_cost']} points for {quota['redeem_bonus']} more, or come back tomorrow."
            ),
        )


def _handle_message(db: Session, user_id: str, message: str) -> dict:
    llm = get_llm_provider()
    result = run_tutor_agent(db, llm, user_id, message)

    db.add(models.ChatMessage(user_id=user_id, role="user", content=message))
    db.add(
        models.ChatMessage(
            user_id=user_id, role="assistant", content=result["content"], citations=result["citations"]
        )
    )
    db.commit()

    record_event(db, user_id, "chat_message")

    append_session_message(user_id, "user", message)
    append_session_message(user_id, "assistant", result["content"])
    return result


@router.post("/message", response_model=schemas.ChatResponse)
def send_message_rest(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """REST fallback for clients that don't use the WebSocket channel."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty")
    if len(payload.message) > 2000:
        raise HTTPException(status_code=400, detail="Please keep questions under 2000 characters")
    _check_quota(db, current_user)
    result = _handle_message(db, current_user.id, payload.message)
    return schemas.ChatResponse(
        role="assistant", content=result["content"], citations=result["citations"],
        quota=gamification.chat_quota(db, current_user),
    )


@router.get("/quota")
def quota(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return gamification.chat_quota(db, current_user)


@router.post("/redeem")
def redeem(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Spend points to unlock extra Elara messages for today."""
    try:
        return gamification.redeem_chat_messages(db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=list[schemas.ChatResponse])
def history(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.created_at)
        .all()
    )
    return [
        schemas.ChatResponse(role=m.role, content=m.content, citations=m.citations or [])
        for m in messages
    ]


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str = Query(...)):
    """
    Streaming chat channel (doc section: `/chat WS`). Auth token passed as a
    query param during the WebSocket handshake, per the doc's auth section.
    """
    try:
        user_id = decode_token(token)
    except Exception:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    db = SessionLocal()
    try:
        while True:
            message = await websocket.receive_text()
            user = db.query(models.User).filter(models.User.id == user_id).first()
            try:
                _check_quota(db, user)
            except HTTPException as e:
                await websocket.send_json({"role": "assistant", "content": e.detail, "citations": [], "error": "quota"})
                continue
            result = _handle_message(db, user_id, message)
            await websocket.send_json(
                {"role": "assistant", "content": result["content"], "citations": result["citations"]}
            )
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
