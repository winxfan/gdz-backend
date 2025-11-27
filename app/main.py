from fastapi import FastAPI, APIRouter, Depends
import logging
import sys
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.api.deps import require_api_key
from app.api.v1 import auth, jobs, transactions, users, webhooks, data, payments, tariffs

def _configure_logging() -> None:
    """Инициализация базовой конфигурации логирования, если не настроена извне.

    Делает видимыми наши application-логи (logger.info(...)) в выводе Uvicorn/Docker.
    """
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    # шумные логгеры — в WARNING
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


_configure_logging()


app = FastAPI(
    title="Neurolibrary API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
)

app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret_key)

# CORS
cors_origins = [
    "http://localhost:3002",
    "https://localhost:3002"
]
if settings.frontend_return_url_base:
    cors_origins.append(settings.frontend_return_url_base)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(jobs.router)
api_v1.include_router(transactions.router, dependencies=[Depends(require_api_key)])
api_v1.include_router(users.router, dependencies=[Depends(require_api_key)])
api_v1.include_router(users.public_router)
api_v1.include_router(data.router, dependencies=[Depends(require_api_key)])
api_v1.include_router(payments.router, dependencies=[Depends(require_api_key)])
api_v1.include_router(tariffs.router, dependencies=[Depends(require_api_key)])
api_v1.include_router(webhooks.router)  # вебхуки без API-ключа

app.include_router(api_v1)

# Публичные колбэки OAuth (без /api/v1), например /oauth/yandex/callback
app.include_router(auth.router_public)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok", "env": settings.environment}
