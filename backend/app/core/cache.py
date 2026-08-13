import json
from functools import lru_cache

from app.core.config import get_settings

_memory_store: dict[str, str] = {}


class _MemoryCache:
    """Fallback used only if Redis isn't reachable, so the app still runs."""

    def get(self, key: str):
        return _memory_store.get(key)

    def set(self, key: str, value: str, ex: int | None = None):
        _memory_store[key] = value

    def delete(self, key: str):
        _memory_store.pop(key, None)


@lru_cache
def get_cache():
    settings = get_settings()
    if settings.redis_url:
        try:
            import redis
            client = redis.from_url(settings.redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            pass
    return _MemoryCache()


def get_session_context(session_id: str) -> list[dict]:
    raw = get_cache().get(f"session:{session_id}")
    return json.loads(raw) if raw else []


def append_session_message(session_id: str, role: str, content: str, max_turns: int = 20):
    history = get_session_context(session_id)
    history.append({"role": role, "content": content})
    history = history[-max_turns:]
    get_cache().set(f"session:{session_id}", json.dumps(history), ex=60 * 60 * 6)
