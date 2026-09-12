"""DB-facing helpers for the scout bot. Kept separate from handlers so the
same logic can later be reused by the FastAPI backend (phase 2) without
duplicating it."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DaySchedule, DayType, Region, Shop, ShopStatus
from app.services.campaign import record_scout_commission
from app.services.common import get_settings, status_for_score
from app.timeutil import TEHRAN_TZ, edit_deadline_for, today_local


async def get_active_region(session: AsyncSession) -> Region | None:
    """The region scouts should be collecting addresses for right now: the
    nearest upcoming distribution day (today or later) that has a target
    region set."""
    today = today_local()
    result = await session.execute(
        select(DaySchedule)
        .where(DaySchedule.day_type == DayType.DISTRIBUTION, DaySchedule.date >= today)
        .order_by(DaySchedule.date.asc())
        .limit(1)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None or schedule.target_region_id is None:
        return None
    return await session.get(Region, schedule.target_region_id)


async def create_shop(
    session: AsyncSession,
    *,
    region_id: int,
    registered_by_id: int,
    name: str,
    address_text: str,
    photo_file_id: str,
    score: int,
    lat: float,
    lng: float,
) -> Shop:
    settings = await get_settings(session)
    today = today_local()
    shop = Shop(
        region_id=region_id,
        registered_by_id=registered_by_id,
        name=name,
        address_text=address_text,
        photo_url=photo_file_id,
        scout_score=score,
        location_lat=lat,
        location_lng=lng,
        status=status_for_score(score, settings.score_threshold),
        editable_until=edit_deadline_for(today),
    )
    session.add(shop)
    await session.commit()
    await session.refresh(shop)
    await record_scout_commission(session, shop)
    return shop


async def get_today_shops_by_scout(session: AsyncSession, scout_id: int) -> list[Shop]:
    """Shops this scout registered today, in Tehran-local terms. Filtered in
    Python rather than SQL since a small daily list per scout never justifies
    a timezone-aware date expression in the query."""
    today = today_local()
    result = await session.execute(
        select(Shop)
        .where(Shop.registered_by_id == scout_id)
        .order_by(Shop.registered_at.desc())
    )
    shops = result.scalars().all()
    return [s for s in shops if s.registered_at.astimezone(TEHRAN_TZ).date() == today]


async def get_scout_owned_shop(session: AsyncSession, shop_id: int, scout_id: int) -> Shop | None:
    result = await session.execute(
        select(Shop).where(Shop.id == shop_id, Shop.registered_by_id == scout_id)
    )
    return result.scalar_one_or_none()


async def update_shop_score(session: AsyncSession, shop: Shop, score: int) -> Shop:
    settings = await get_settings(session)
    shop.scout_score = score
    # Only bump status off AWAITING_THRESHOLD / QUEUED_FOR_PACK — never touch a
    # shop that has already moved further down the pipeline.
    if shop.status in (ShopStatus.AWAITING_THRESHOLD, ShopStatus.QUEUED_FOR_PACK):
        shop.status = status_for_score(score, settings.score_threshold)
    await session.commit()
    return shop


async def update_shop_name(session: AsyncSession, shop: Shop, name: str) -> Shop:
    shop.name = name
    await session.commit()
    return shop


async def update_shop_address(session: AsyncSession, shop: Shop, address_text: str) -> Shop:
    shop.address_text = address_text
    await session.commit()
    return shop


async def update_shop_photo(session: AsyncSession, shop: Shop, photo_file_id: str) -> Shop:
    shop.photo_url = photo_file_id
    await session.commit()
    return shop


async def update_shop_location(session: AsyncSession, shop: Shop, lat: float, lng: float) -> Shop:
    shop.location_lat = lat
    shop.location_lng = lng
    await session.commit()
    return shop
