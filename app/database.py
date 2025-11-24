import os
from typing import Tuple, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings


def _build_conn() -> Tuple[str, Dict[str, Any]]:
    # 1) Явные POSTGRES_* имеют приоритет (MDB кластер)
    host_env = os.getenv("POSTGRES_HOST", "").strip()
    if host_env:
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "postgres")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        sslrootcert = os.getenv("POSTGRES_SSLROOTCERT", "/certs/root.crt")

        first_host = host_env.split(",")[0].strip()
        url = f"postgresql://{user}:{password}@{first_host}:{port}/{database}"
        connect_args: Dict[str, Any] = {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "verify-full"),
            "sslrootcert": sslrootcert,
            "target_session_attrs": "primary",
            "application_name": "kreatum_backend",
            "connect_timeout": 30,
            "keepalives_idle": 600,
            "keepalives_interval": 30,
            "keepalives_count": 3,
        }
        return url, connect_args

    # 2) Если задана DATABASE_URL в окружении — используем её
    env_database_url = os.getenv("DATABASE_URL", "").strip()
    if env_database_url:
        connect_args: Dict[str, Any] = {}
        sslrootcert = os.getenv("POSTGRES_SSLROOTCERT")
        if sslrootcert:
            connect_args.update({
                "sslmode": os.getenv("POSTGRES_SSLMODE", "verify-full"),
                "sslrootcert": sslrootcert,
                "target_session_attrs": "primary",
                "application_name": "kreatum_backend",
                "connect_timeout": 30,
                "keepalives_idle": 600,
                "keepalives_interval": 30,
                "keepalives_count": 3,
            })
        return env_database_url, connect_args

    # 3) Фоллбэк — дефолт из настроек (подходит, если есть сервис postgres в docker-compose)
    return settings.database_url, {}


database_url, connect_args = _build_conn()

engine = create_engine(
    database_url,
    connect_args=connect_args,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=60,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


