import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import create_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
COLORS = ["#e50914", "#f5a623", "#14b8a6", "#6366f1", "#ec4899", "#22c55e", "#0ea5e9", "#a855f7"]


class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=6, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def user_out(u: User) -> dict:
    return dict(
        id=u.id, email=u.email, username=u.username, bio=u.bio, avatar_color=u.avatar_color,
        fav_genres=[g for g in u.fav_genres.split(",") if g], onboarded=u.onboarded,
        is_admin=u.is_admin, created_at=u.created_at.isoformat(),
    )


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    u = User(email=email, username=body.username.strip(), password_hash=hash_password(body.password),
             avatar_color=random.choice(COLORS))
    db.add(u)
    db.commit()
    return dict(token=create_token(u.id), user=user_out(u))


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email.lower()).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return dict(token=create_token(u.id), user=user_out(u))


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)
