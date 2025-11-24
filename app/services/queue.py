from __future__ import annotations

from redis import Redis
from rq import Queue
from app.core.config import settings


def get_queue(name: str = "default") -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue(name, connection=redis_conn)

