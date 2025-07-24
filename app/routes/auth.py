from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.auth import schemas
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=schemas.UserOut)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return auth_service.register_user(user, db)


@router.post("/login")
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    return auth_service.login_user(credentials, db)


@router.get("/me")
def get_me(request: Request):
    # пока заглушка, можно заменить позже на полноценный decode
    return {
        "sub": "admin",
        "role": "admin"
    }


@router.post("/logout")
def logout():
    return auth_service.logout_user()
