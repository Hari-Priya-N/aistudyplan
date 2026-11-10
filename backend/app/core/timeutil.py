"""Timezone helpers. The DB stores naive UTC; "today" is the school's local day."""
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def _tz() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().app_timezone)
    except Exception:  # unknown zone / missing tzdata -> fall back to UTC
        return ZoneInfo("UTC")


def utcnow() -> datetime:
    return datetime.utcnow()


def local_date(dt_utc: datetime) -> date:
    """Local calendar date of a naive-UTC datetime."""
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(_tz()).date()


def local_day_start_utc(days_ago: int = 0) -> datetime:
    """Naive-UTC datetime of local midnight, `days_ago` days back."""
    now_local = datetime.now(_tz())
    midnight = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_ago)
    return midnight.astimezone(timezone.utc).replace(tzinfo=None)
