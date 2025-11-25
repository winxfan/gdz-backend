from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import User
from app.services.user_profile import avatar_id_for_ip, username_for_ip

router = APIRouter(prefix="/users", tags=["Users"])
public_router = APIRouter(tags=["Users"])


def _serialize_public_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "avatarId": user.avatar_id,
        "avatarUrl": user.avatar_url,
        "tokens": float(user.balance_tokens or 0),
        "tokensUsedAsAnon": user.tokens_used_as_anon or 0,
        "isAuthorized": bool(user.is_authorized),
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
    }


def _serialize_admin_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "ip": user.ip,
        "username": user.username,
        "avatarId": user.avatar_id,
        "avatarUrl": user.avatar_url,
        "balanceTokens": float(user.balance_tokens or 0),
        "tokensUsedAsAnon": user.tokens_used_as_anon or 0,
        "isAuthorized": bool(user.is_authorized),
        "consentPd": user.consent_pd,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "updatedAt": user.updated_at.isoformat() if user.updated_at else None,
    }


def _create_user_for_ip(db: Session, ip: str) -> User:
    user = User(
        id=uuid.uuid4(),
        ip=ip,
        username=username_for_ip(ip),
        avatar_id=avatar_id_for_ip(ip),
        anon_user_id=str(uuid.uuid4()),
        balance_tokens=Decimal("5"),
        tokens_used_as_anon=0,
        is_authorized=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _find_user_by_ip(db: Session, ip: str) -> User | None:
    return db.query(User).filter(User.ip == ip).first()


@public_router.post("/auth-user")
def auth_user(x_user_ip: str = Header(alias="x-user-ip"), db: Session = Depends(get_db)) -> dict:
    ip = (x_user_ip or "").strip()
    if not ip:
        raise HTTPException(status_code=400, detail="Missing x-user-ip header")
    user = _find_user_by_ip(db, ip)
    if not user:
        user = _create_user_for_ip(db, ip)
    return _serialize_public_user(user)


@router.get("/{user_id}")
def get_user_by_id(user_id: str, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_admin_user(user)
