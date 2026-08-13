from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.agent.remediation import generate_remediation
from app.core.security import get_current_user
from app.database import get_db
from app.llm.factory import get_llm_provider

router = APIRouter(prefix="/remediation", tags=["remediation"])


@router.post("/micro-module", response_model=schemas.RemediationOut)
def micro_module(
    payload: schemas.RemediationRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    llm = get_llm_provider()
    try:
        result = generate_remediation(
            db, llm, current_user.id, payload.topic_id, payload.sub_concept
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return schemas.RemediationOut(**result)
