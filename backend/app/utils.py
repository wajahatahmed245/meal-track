from datetime import date, datetime, timedelta, timezone

_PKT = timezone(timedelta(hours=5))


def today_pkt() -> date:
    """Return the current calendar date in Pakistan Standard Time (UTC+5)."""
    return datetime.now(_PKT).date()
