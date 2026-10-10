from collections import defaultdict, deque
from hashlib import sha256
from threading import Lock
from time import monotonic

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_memory: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()
_redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.25,
    socket_timeout=0.25,
)


def allow_attempt(scope: str, identity: str, *, limit: int, window_seconds: int) -> bool:
    """Redis-backed fixed-window throttle with a bounded local fallback in development.

    In production, Redis failure fails closed. Identity values are hashed before use as
    Redis keys to avoid putting usernames or network identifiers into key names.
    """
    key_hash = sha256(identity.encode("utf-8")).hexdigest()
    key = f"aramesh:limit:{scope}:{key_hash}"
    try:
        pipe = _redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        count, _ = pipe.execute()
        return int(count) <= limit
    except RedisError:
        if settings.environment.lower() == "production":
            return False
        now = monotonic()
        with _lock:
            events = _memory[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True
