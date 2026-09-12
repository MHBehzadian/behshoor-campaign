"""Demo/dev data for trying out the webapp locally. NOT for production —
creates a few obvious test accounts.

Usage (from backend/, with DATABASE_URL pointed at a migrated dev DB):
    python scripts/seed_preview_data.py
"""
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import async_session  # noqa: E402
from app.models import DaySchedule, DayType, Region, Shop, ShopStatus, User, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import campaign  # noqa: E402
from app.timeutil import today_local  # noqa: E402


async def seed() -> None:
    async with async_session() as session:
        admin = User(role=UserRole.ADMIN, full_name="ادمین اصلی", username="admin", password_hash=hash_password("admin123"))
        visitor1 = User(role=UserRole.VISITOR, full_name="ویزیتور یک", username="visitor1", password_hash=hash_password("visitor123"), visitor_subteam=1)
        visitor2 = User(role=UserRole.VISITOR, full_name="ویزیتور دو", username="visitor2", password_hash=hash_password("visitor123"), visitor_subteam=2)
        dist1 = User(role=UserRole.DISTRIBUTOR, full_name="پخش یک", username="dist1", password_hash=hash_password("dist123"))
        scout = User(role=UserRole.SCOUT, full_name="در‌آور تست", telegram_id=100000001)
        session.add_all([admin, visitor1, visitor2, dist1, scout])
        await session.flush()

        region1 = Region(name="ناحیه ۱ - مرکز شهر")
        region2 = Region(name="ناحیه ۲ - گاوازنگ")
        session.add_all([region1, region2])
        await session.flush()

        today = today_local()
        session.add(
            DaySchedule(date=today, day_type=DayType.DISTRIBUTION, target_region_id=region1.id, created_by_id=admin.id)
        )
        session.add(
            DaySchedule(date=today + timedelta(days=1), day_type=DayType.FOLLOWUP, created_by_id=admin.id)
        )
        await session.flush()

        shops_data = [
            ("سوپرمارکت رضا", "خیابان امام، پلاک ۱۲", 3, 36.6736, 48.4787, ShopStatus.QUEUED_FOR_PACK),
            ("بقالی محمدی", "کوچه‌ی گلستان، پلاک ۵", 3, 36.6745, 48.4795, ShopStatus.QUEUED_FOR_PACK),
            ("فروشگاه زنجان", "میدان انقلاب، پلاک ۳", 2, 36.6720, 48.4770, ShopStatus.AWAITING_THRESHOLD),
            ("سوپر مارکت پارک", "خیابان طالقانی، پلاک ۸", 3, 36.6760, 48.4810, ShopStatus.PACK_DELIVERED),
            ("خشکبار امید", "خیابان سعدی، پلاک ۲۰", 3, 36.6700, 48.4750, ShopStatus.ORDER1_PENDING_DELIVERY),
        ]
        for name, address, score, lat, lng, status in shops_data:
            shop = Shop(
                region_id=region1.id,
                registered_by_id=scout.id,
                name=name,
                address_text=address,
                photo_url="dev-placeholder",
                scout_score=score,
                location_lat=lat,
                location_lng=lng,
                status=status,
            )
            session.add(shop)
            await session.flush()
            await campaign.record_scout_commission(session, shop)

        await session.commit()
        print("Seeded demo data. Login with: admin/admin123, visitor1/visitor123, visitor2/visitor123, dist1/dist123")


if __name__ == "__main__":
    asyncio.run(seed())
