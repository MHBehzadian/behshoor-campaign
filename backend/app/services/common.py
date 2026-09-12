"""Shared between the scout bot and the FastAPI backend — the score/threshold
rule must never drift between the two entry points."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Settings, ShopStatus


async def get_settings(session: AsyncSession) -> Settings:
    result = await session.execute(select(Settings).where(Settings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        # Phase 0's migration seeds row id=1; this is just a defensive fallback.
        settings = Settings(id=1)
        session.add(settings)
        await session.commit()
    return settings


def status_for_score(score: int, threshold: int) -> ShopStatus:
    return ShopStatus.QUEUED_FOR_PACK if score >= threshold else ShopStatus.AWAITING_THRESHOLD
