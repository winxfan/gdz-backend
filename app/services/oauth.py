from __future__ import annotations

from typing import Any

from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from app.core.config import settings


class OAuthService:
    _oauth: OAuth | None = None

    @classmethod
    def get_oauth(cls) -> OAuth:
        if cls._oauth is None:
            # Читаем только из переменных окружения, без .env файла (чтобы не было ворнинга в контейнере)
            config = Config()
            oauth = OAuth(config)

            # Google OpenID Connect
            oauth.register(
                name="google",
                client_id=settings.oauth_google_client_id,
                client_secret=settings.oauth_google_client_secret,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                client_kwargs={"scope": "openid email profile"},
            )

            # VK OAuth2
            oauth.register(
                name="vk",
                client_id=settings.oauth_vk_client_id,
                client_secret=settings.oauth_vk_client_secret,
                access_token_url="https://oauth.vk.com/access_token",
                authorize_url="https://oauth.vk.com/authorize",
                api_base_url="https://api.vk.com/method",
                client_kwargs={"scope": "email"},
            )

            # Yandex OAuth2
            oauth.register(
                name="yandex",
                client_id=settings.oauth_yandex_client_id,
                client_secret=settings.oauth_yandex_client_secret,
                access_token_url="https://oauth.yandex.ru/token",
                authorize_url="https://oauth.yandex.ru/authorize",
                api_base_url="https://login.yandex.ru/",
                client_kwargs={"scope": "login:email login:info"},
            )

            cls._oauth = oauth
        return cls._oauth


oauth_service = OAuthService()


