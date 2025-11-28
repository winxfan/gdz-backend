from __future__ import annotations

from typing import Any
import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.base_client.errors import OAuthError
import structlog
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.oauth import oauth_service
from sqlalchemy.orm import Session
from app.database import get_db
from app.db.models import User, Job, Transaction
from app.services.user_profile import avatar_id_for_ip, username_for_ip
from app.services.vk_id import get_vk_id_service, VkIdError

router = APIRouter(prefix="/auth", tags=["auth"]) 
router_public = APIRouter(tags=["auth"])  # публичные колбэки без /api/v1
logger = structlog.get_logger(__name__)


def _validate_provider(provider: str) -> None:
    if provider not in ("google", "vk", "yandex"):
        raise HTTPException(status_code=404, detail="Unknown provider")


def _extract_identity(provider: str, token: dict[str, Any], userinfo: dict[str, Any] | None) -> dict[str, Any]:
    social_id = None
    email = None
    name = None
    first_name = None

    if provider == "google" and userinfo:
        social_id = userinfo.get("sub")
        email = userinfo.get("email")
        name = userinfo.get("name")
        first_name = userinfo.get("given_name") or (name.split(" ", 1)[0] if isinstance(name, str) else None)
    elif provider == "yandex" and userinfo:
        social_id = userinfo.get("id")
        email = userinfo.get("default_email") or userinfo.get("emails", [None])[0]
        name = userinfo.get("real_name") or userinfo.get("display_name")
        first_name = userinfo.get("first_name") or (name.split(" ", 1)[0] if isinstance(name, str) else None)
    elif provider == "vk":
        social_id = token.get("user_id")
        email = token.get("email")
        name = token.get("first_name")
        first_name = token.get("first_name")

    if social_id:
        social_id = f"{provider}:{social_id}"

    return {"social_id": social_id, "email": email, "name": name, "first_name": first_name}


def _merge_users(db: Session, target: User, source: User) -> None:
    target.balance_tokens = (target.balance_tokens or Decimal("0")) + (source.balance_tokens or Decimal("0"))
    target.tokens_used_as_anon = max(target.tokens_used_as_anon or 0, source.tokens_used_as_anon or 0)
    if source.username:
        target.username = source.username
    if source.avatar_id:
        target.avatar_id = source.avatar_id
    if source.ip:
        target.ip = source.ip
    db.query(Job).filter(Job.user_id == source.id).update({Job.user_id: target.id})
    db.query(Transaction).filter(Transaction.user_id == source.id).update({Transaction.user_id: target.id})
    db.delete(source)


def _link_user(
    db: Session,
    identity: dict[str, Any],
    ip_hint: str | None,
) -> User:
    social_id = identity.get("social_id")
    email = identity.get("email")

    user: User | None = None
    if social_id:
        user = db.query(User).filter(User.social_id == social_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    anon_user: User | None = None
    if ip_hint:
        anon_user = db.query(User).filter(User.ip == ip_hint).first()

    if user and anon_user and user.id != anon_user.id:
        _merge_users(db, user, anon_user)
        db.commit()
        db.refresh(user)

    target = user or anon_user
    display_name = identity.get("first_name") or identity.get("name")

    if not target:
        username_seed = display_name or ip_hint or email or social_id or str(uuid.uuid4())
        target = User(
            ip=ip_hint,
            username=display_name or username_for_ip(username_seed),
            avatar_id=avatar_id_for_ip(username_seed),
            anon_user_id=str(uuid.uuid4()),
            balance_tokens=Decimal("5"),
            tokens_used_as_anon=0,
        )
        db.add(target)

    if social_id:
        target.social_id = social_id
    if email:
        target.email = email
    if display_name:
        target.username = display_name
    target.is_authorized = True
    if ip_hint:
        target.ip = ip_hint

    db.commit()
    db.refresh(target)
    return target


def _serialize_public_user(user: User) -> dict[str, Any]:
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


class VkIdExchangePayload(BaseModel):
    code: str
    device_id: str = Field(..., alias="deviceId")
    code_verifier: str = Field(..., alias="codeVerifier")
    state: str | None = None


@router.post("/oauth/vk-id/exchange")
def vk_id_exchange(
    payload: VkIdExchangePayload,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    service = get_vk_id_service()
    try:
        token_payload = service.exchange_code(
            code=payload.code,
            device_id=payload.device_id,
            code_verifier=payload.code_verifier,
        )
        identity = service.build_identity(token_payload)
    except VkIdError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    ip_hint = request.headers.get("x-user-ip") or request.cookies.get("user_ip")
    user = _link_user(db, identity, ip_hint)
    return _serialize_public_user(user)


async def _handle_oauth_callback(request: Request, provider: str, db: Session) -> RedirectResponse:
    oauth = oauth_service.get_oauth()
    _validate_provider(provider)
    client = getattr(oauth, provider)

    # Совпадающий redirect_uri на этапе обмена кода (важно для Яндекс)
    if provider == "yandex":
        callback_url = request.url_for("oauth_callback_public", provider=provider)
    else:
        callback_url = request.url_for("oauth_callback", provider=provider)

    try:
        # redirect_uri уже сохранён в сессии после authorize_redirect; повторная передача ломает вызов
        token = await client.authorize_access_token(request)
    except OAuthError as exc:
        logger.warning("oauth_authorize_access_token_failed", provider=provider, error=str(exc))
        frontend_base = settings.frontend_return_url_base or "https://xn--80aqu.xn-----glcep7bbaf7au.xn--p1ai"
        return RedirectResponse(url=f"{frontend_base}/profile?auth_error={exc.error}&provider={provider}")

    userinfo: dict[str, Any] | None = None
    if provider == "google":
        userinfo = token.get("userinfo")
    elif provider == "yandex":
        try:
            resp = await client.get("https://login.yandex.ru/info", params={"format": "json"}, token=token)
            userinfo = resp.json() if resp else None
        except OAuthError as exc:
            logger.warning("oauth_userinfo_failed", provider=provider, error=str(exc))
            frontend_base = settings.frontend_return_url_base or "https://xn--80aqu.xn-----glcep7bbaf7au.xn--p1ai"
            return RedirectResponse(url=f"{frontend_base}/profile?auth_error=userinfo_failed&provider={provider}")
    elif provider == "vk":
        userinfo = {
            "user_id": token.get("user_id"),
            "email": token.get("email"),
            "access_token": token.get("access_token"),
        }

    identity = _extract_identity(provider, token, userinfo)
    ip_hint = request.headers.get("x-user-ip") or request.cookies.get("user_ip")
    try:
        user = _link_user(db, identity, ip_hint)
        logger.info("oauth_user_linked", provider=provider, user_id=str(user.id))
    except Exception as exc:
        logger.exception("oauth_user_link_failed", provider=provider)
        frontend_base = settings.frontend_return_url_base or "https://xn--80aqu.xn-----glcep7bbaf7au.xn--p1ai"
        return RedirectResponse(url=f"{frontend_base}/profile?auth_error=link_failed&provider={provider}")

    frontend_base = settings.frontend_return_url_base or "https://xn--80aqu.xn-----glcep7bbaf7au.xn--p1ai"
    redirect_url = f"{frontend_base}/profile?userId={user.id}"
    return RedirectResponse(url=redirect_url)


@router.get("/oauth/{provider}/login")
async def oauth_login(request: Request, provider: str):
    oauth = oauth_service.get_oauth()
    _validate_provider(provider)

    # Для Яндекса используем публичный колбэк без /api/v1
    if provider == "yandex":
        callback_url = request.url_for("oauth_callback_public", provider=provider)
    else:
        callback_url = request.url_for("oauth_callback", provider=provider)
    client = getattr(oauth, provider)
    return await client.authorize_redirect(request, str(callback_url))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(request: Request, provider: str, db: Session = Depends(get_db)):
    return await _handle_oauth_callback(request, provider, db)


# Публичный колбэк без префикса /api/v1, чтобы совпадал с настройками у Яндекса
@router_public.get("/oauth/{provider}/callback")
async def oauth_callback_public(request: Request, provider: str, db: Session = Depends(get_db)):
    return await _handle_oauth_callback(request, provider, db)


@router.get("/user/me")
def user_me() -> dict:
    return {"id": "stub", "name": "Guest", "balance_tokens": 0}


# Временный алиас, чтобы фронт не падал на /api/v1/auth/me
@router.get("/me")
def user_me_alias() -> dict:
    return user_me()

