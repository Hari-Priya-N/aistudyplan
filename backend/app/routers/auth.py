from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.database import get_db
from app.services import gamification
from app.services.activity import start_session

router = APIRouter(prefix="/auth", tags=["auth"])

# Self-service sign-up is open to students and faculty. Management accounts are
# created by the server (ADMIN_EMAIL / ADMIN_PASSWORD env vars, or the demo seed).
SIGNUP_ROLES = {
    "student": models.RoleEnum.student,
    "faculty": models.RoleEnum.instructor,
    "instructor": models.RoleEnum.instructor,
}


def _find_user(db: Session, identifier: str) -> models.User | None:
    ident = identifier.strip()
    user = db.query(models.User).filter(func.lower(models.User.email) == ident.lower()).first()
    if not user:  # students can also sign in with their roll / admission number
        user = db.query(models.User).filter(func.lower(models.User.roll_no) == ident.lower()).first()
    return user


def _login(db: Session, user: models.User) -> schemas.Token:
    start_session(db, user)
    gamification.on_login(db, user)
    return schemas.Token(access_token=create_access_token(subject=user.id))


@router.post("/signup", response_model=schemas.Token, status_code=201)
def signup(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(models.User).filter(func.lower(models.User.email) == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    role = SIGNUP_ROLES.get(payload.role)
    if role is None:
        raise HTTPException(status_code=400, detail="You can sign up as a student or faculty member")

    user = models.User(
        email=email, hashed_password=hash_password(payload.password), role=role,
        full_name=(payload.full_name or "").strip() or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _login(db, user)


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = _find_user(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email/roll number or password")
    return _login(db, user)


@router.post("/token", response_model=schemas.Token)
def token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login — used by the 'Authorize' button in /docs."""
    user = _find_user(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return schemas.Token(access_token=create_access_token(subject=user.id))


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.must_change_password = False
    db.add(current_user)
    db.commit()
    return {"status": "password_changed"}
