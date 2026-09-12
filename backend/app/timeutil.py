"""All bot-side date/time logic assumes a single deployment timezone (Iran)."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

TEHRAN_TZ = ZoneInfo("Asia/Tehran")
EDIT_DEADLINE = time(18, 0)  # 6pm — soft deadline, informational only


def now_local() -> datetime:
    return datetime.now(TEHRAN_TZ)


def today_local() -> date:
    return now_local().date()


def day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=TEHRAN_TZ)


def edit_deadline_for(d: date) -> datetime:
    return datetime.combine(d, EDIT_DEADLINE, tzinfo=TEHRAN_TZ)
