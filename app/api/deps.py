from fastapi import Header, HTTPException
from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    # В dev-режиме без ключа — пропускаем
    if not settings.server_api_key:
        return
    if x_api_key != settings.server_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")




