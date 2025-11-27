from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


class VkIdError(RuntimeError):
    pass


class VkIdService:
    token_url = "https://id.vk.ru/oauth2/auth"
    users_api_url = "https://api.vk.com/method/users.get"

    def __init__(self) -> None:
        if not settings.oauth_vk_client_id or not settings.oauth_vk_client_secret:
            raise RuntimeError("VK OAuth credentials are not configured")
        self.client_id = settings.oauth_vk_client_id
        self.client_secret = settings.oauth_vk_client_secret
        self.service_key = settings.oauth_vk_client_service_key

    def exchange_code(self, code: str, device_id: str, code_verifier: str) -> dict[str, Any]:
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "device_id": device_id,
            "code_verifier": code_verifier,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(self.token_url, data=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            text = exc.response.text
            logger.warning("vk_id.exchange_failed", status=exc.response.status_code, body=text)
            raise VkIdError(f"VK ID exchange failed: {text}") from exc
        except Exception as exc:
            logger.exception("vk_id.exchange_error")
            raise VkIdError("VK ID exchange error") from exc
        return data

    def _decode_id_token(self, id_token: str | None) -> dict[str, Any]:
        if not id_token:
            return {}
        try:
            return jwt.decode(id_token, options={"verify_signature": False, "verify_aud": False})
        except jwt.PyJWTError:
            logger.warning("vk_id.id_token_decode_failed")
            return {}

    def _fetch_user_profile(self, user_id: str | None) -> dict[str, Any]:
        if not user_id or not self.service_key:
            return {}
        params = {
            "user_ids": user_id,
            "fields": "first_name,last_name,photo_200,email",
            "access_token": self.service_key,
            "v": "5.199",
        }
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(self.users_api_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.warning("vk_id.users_get_failed", exc_info=True)
            return {}
        response = (data or {}).get("response")
        if isinstance(response, list) and response:
            return response[0]
        return {}

    def build_identity(self, token_payload: dict[str, Any]) -> dict[str, Optional[str]]:
        id_token = token_payload.get("id_token")
        claims = self._decode_id_token(id_token)

        raw_user_id = (
            token_payload.get("user_id")
            or claims.get("sub")
            or claims.get("user_id")
        )
        email = token_payload.get("email") or claims.get("email")
        first_name = token_payload.get("first_name") or claims.get("given_name") or claims.get("first_name")
        last_name = token_payload.get("last_name") or claims.get("family_name") or claims.get("last_name")
        full_name = token_payload.get("name") or claims.get("name")

        if not first_name or not full_name:
            profile = self._fetch_user_profile(raw_user_id)
            first_name = first_name or profile.get("first_name")
            last_name = last_name or profile.get("last_name")
            if not full_name:
                parts = [first_name, last_name]
                full_name = " ".join([p for p in parts if p]) or None
            email = email or profile.get("email")

        social_id = f"vk:{raw_user_id}" if raw_user_id else None
        return {
            "social_id": social_id,
            "email": email,
            "first_name": first_name,
            "name": full_name,
        }


_vk_id_service: VkIdService | None = None


def get_vk_id_service() -> VkIdService:
    global _vk_id_service
    if _vk_id_service is None:
        _vk_id_service = VkIdService()
    return _vk_id_service


