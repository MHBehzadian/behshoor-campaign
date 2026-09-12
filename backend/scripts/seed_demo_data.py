"""One-off script to get the bot testable before the admin website (phase 3)
exists. Creates a couple of regions, an admin, a scout you can log in as, and
schedules tomorrow as a distribution day for the first region.

Usage (from backend/):
    python scripts/seed_demo_data.py --scout-telegram-id 123456789 --scout-name "علی"
"""
import argparse
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import async_session  # noqa: E402
from app.models import DaySchedule, DayType, Region, User, UserRole  # noqa: E402
from app.timeutil import today_local  # noqa: E402


async def seed(scout_telegram_id: int, scout_name: str) -> None:
    async with async_session() as session:
        admin = User(role=UserRole.ADMIN, full_name="ادمین", telegram_id=None)
        scout = User(role=UserRole.SCOUT, full_name=scout_name, telegram_id=scout_telegram_id)
        session.add_all([admin, scout])
        await session.flush()

        region_a = Region(name="ناحیه ۱ - مرکز شهر")
        region_b = Region(name="ناحیه ۲ - گاوازنگ")
        session.add_all([region_a, region_b])
        await session.flush()

        tomorrow = today_local() + timedelta(days=1)
        session.add(
            DaySchedule(
                date=tomorrow,
                day_type=DayType.DISTRIBUTION,
                target_region_id=region_a.id,
                created_by_id=admin.id,
            )
        )
        await session.commit()

        print(f"Seeded: admin(id={admin.id}), scout(id={scout.id}, tg={scout_telegram_id})")
        print(f"Regions: {region_a.name} (id={region_a.id}), {region_b.name} (id={region_b.id})")
        print(f"Active region for the bot as of today: {region_a.name} (tomorrow={tomorrow})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout-telegram-id", type=int, required=True)
    parser.add_argument("--scout-name", type=str, default="در‌آور تست")
    args = parser.parse_args()
    asyncio.run(seed(args.scout_telegram_id, args.scout_name))
