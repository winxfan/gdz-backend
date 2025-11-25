from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from decimal import Decimal

from app.database import get_db
from app.db.models import User, Transaction

router = APIRouter(prefix="/users", tags=["Users"]) 


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "ip": user.ip,
        "username": user.username,
        "avatarId": user.avatar_id,
        "avatarUrl": user.avatar_url,
        "balanceTokens": float(user.balance_tokens or 0),
        "consentPd": user.consent_pd,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
    }

# anon user
@router.post("/register-or-login")
def register_or_login(payload: dict, db: Session = Depends(get_db)) -> dict:
    
    return _serialize_user(user)

#  anon user oauth by user id
@router.post("/register-or-login")
def register_or_login(payload: dict, db: Session = Depends(get_db)) -> dict:
    
    return _serialize_user(user)


@router.get("/{user_id}")
def get_user_by_id(user_id: str, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(user)

