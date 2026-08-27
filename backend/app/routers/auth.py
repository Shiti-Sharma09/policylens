from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlmodel import Session, select

from app.db import get_session
from app.dependencies import get_current_user
from app.models.models import User
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    # bcrypt hard-caps input at 72 bytes; 72 chars is a safe under-approximation for ASCII passwords
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.get("/ping")
def ping():
    return {"router": "auth", "status": "stub"}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(email=body.email, hashed_password=hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == body.email)).first()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(user_id=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return UserResponse(id=current_user.id, email=current_user.email)
