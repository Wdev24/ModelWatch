"""
Single RQ queue for monitoring jobs. Kept to one queue/one worker type for
V1 (spec section 13: no distributed workflow engine).
"""
from redis import Redis
from rq import Queue

from app.core.config import get_settings

_settings = get_settings()
_redis_conn = Redis.from_url(_settings.redis_url)

monitoring_queue = Queue("monitoring", connection=_redis_conn)
