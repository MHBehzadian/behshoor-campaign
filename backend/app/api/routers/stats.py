from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin
from app.api.schemas import RegionStatsOut
from app.models import Region, Shop, ShopStatus

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_admin)])

# Buckets mirror the simplified state machine in app/services/campaign.py —
# PACK_DELIVERED and ORDER1_DONE double as "awaiting the next follow-up".
ADVERTISED = {
    ShopStatus.PACK_DELIVERED,
    ShopStatus.ORDER1_PENDING_DELIVERY,
    ShopStatus.ORDER1_DONE,
    ShopStatus.ORDER2_PENDING_DELIVERY,
    ShopStatus.STEADY_CUSTOMER,
}
IN_FOLLOWUP = {ShopStatus.PACK_DELIVERED, ShopStatus.ORDER1_DONE}
ORDER1_PLACED = {
    ShopStatus.ORDER1_PENDING_DELIVERY,
    ShopStatus.ORDER1_DONE,
    ShopStatus.ORDER2_PENDING_DELIVERY,
    ShopStatus.STEADY_CUSTOMER,
}
ORDER2_PLACED = {ShopStatus.ORDER2_PENDING_DELIVERY, ShopStatus.STEADY_CUSTOMER}


@router.get("/regions", response_model=list[RegionStatsOut])
async def region_stats(session: AsyncSession = SessionDep) -> list[dict]:
    """One row per region: how many shops are registered / advertised /
    mid-follow-up / have placed order 1 or 2 / are steady customers /
    dropped. Backs the admin dashboard's summary table."""
    result = await session.execute(
        select(Shop.region_id, Shop.status, func.count()).group_by(Shop.region_id, Shop.status)
    )
    rows = result.all()

    regions = (await session.execute(select(Region))).scalars().all()
    by_region = {
        r.id: {
            "region_id": r.id,
            "region_name": r.name,
            "total": 0,
            "advertised": 0,
            "in_followup": 0,
            "order1_placed": 0,
            "order2_placed": 0,
            "steady_customer": 0,
            "dropped": 0,
        }
        for r in regions
    }

    for region_id, status, count in rows:
        bucket = by_region.get(region_id)
        if bucket is None:
            continue
        bucket["total"] += count
        if status in ADVERTISED:
            bucket["advertised"] += count
        if status in IN_FOLLOWUP:
            bucket["in_followup"] += count
        if status in ORDER1_PLACED:
            bucket["order1_placed"] += count
        if status in ORDER2_PLACED:
            bucket["order2_placed"] += count
        if status == ShopStatus.STEADY_CUSTOMER:
            bucket["steady_customer"] += count
        if status == ShopStatus.DROPPED:
            bucket["dropped"] += count

    return list(by_region.values())
