from __future__ import annotations

from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.base_client.errors import OAuthError
import structlog

from app.core.config import settings
from app.services.oauth import oauth_service
from sqlalchemy.orm import Session
from app.database import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"]) 
router_public = APIRouter(tags=["auth"])  # публичные колбэки без /api/v1
logger = structlog.get_logger(__name__)


def _validate_provider(provider: str) -> None:
    if provider not in ("google", "vk", "yandex"):
        raise HTTPException(status_code=404, detail="Unknown provider")


async def _handle_oauth_callback(request: Request, provider: str) -> RedirectResponse:
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
        frontend_base = settings.frontend_return_url_base or "https://xn--b1ahgb0aea5aq.online"
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
            frontend_base = settings.frontend_return_url_base or "https://xn--b1ahgb0aea5aq.online"
            return RedirectResponse(url=f"{frontend_base}/profile?auth_error=userinfo_failed&provider={provider}")
    elif provider == "vk":
        userinfo = {
            "user_id": token.get("user_id"),
            "email": token.get("email"),
            "access_token": token.get("access_token"),
        }

    frontend_base = settings.frontend_return_url_base or "https://xn--b1ahgb0aea5aq.online"
    redirect_url = f"{frontend_base}/profile"
    return RedirectResponse(url=redirect_url)


@router.get("/oauth/{provider}/login")
async def oauth_login(request: Request, provider: str, db: Session = Depends(get_db)):
    oauth = oauth_service.get_oauth()
    _validate_provider(provider)

    # Создаём пользователя, если его ещё нет
    session = request.session
    anon_user_id: str | None = session.get("anon_user_id")
    if not anon_user_id:
        anon_user_id = str(uuid.uuid4())
        session["anon_user_id"] = anon_user_id

    try:
        existing = db.query(User).filter(User.anon_user_id == anon_user_id).first()
        if existing is None:
            user = User(anon_user_id=anon_user_id)
            db.add(user)
            db.commit()
    except Exception as exc:  # не блокируем OAuth редирект при проблемах с БД
        logger.warning("oauth_login_user_init_failed", error=str(exc))

    # Для Яндекса используем публичный колбэк без /api/v1
    if provider == "yandex":
        callback_url = request.url_for("oauth_callback_public", provider=provider)
    else:
        callback_url = request.url_for("oauth_callback", provider=provider)
    client = getattr(oauth, provider)
    return await client.authorize_redirect(request, str(callback_url))


@router.get("/oauth/{provider}/callback")
async def oauth_callback(request: Request, provider: str):
    return await _handle_oauth_callback(request, provider)


# Публичный колбэк без префикса /api/v1, чтобы совпадал с настройками у Яндекса
@router_public.get("/oauth/{provider}/callback")
async def oauth_callback_public(request: Request, provider: str):
    return await _handle_oauth_callback(request, provider)


@router.get("/user/me")
def user_me() -> dict:
    return {"id": "stub", "name": "Guest", "balance_tokens": 0}


# Временный алиас, чтобы фронт не падал на /api/v1/auth/me
@router.get("/me")
def user_me_alias() -> dict:
    return user_me()

