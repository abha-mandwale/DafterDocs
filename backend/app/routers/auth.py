from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..db import get_db
from ..models import User
from ..schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic


router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/register', response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Email already exists.')

    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role='member',
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(
        token=token,
        user=UserPublic(id=user.id, name=user.name, email=user.email, role=user.role),
    )


@router.post('/login', response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials.')

    token = create_access_token(user.id)
    return AuthResponse(
        token=token,
        user=UserPublic(id=user.id, name=user.name, email=user.email, role=user.role),
    )
