from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_visitor
from app.api.schemas import PackDeliveryCreate, RegionOut, ShopOut
from app.models import Shop, User
from app.services import campaign

router = APIRouter(prefix="/pack-deliveries", tags=["pack-deliveries"])


@router.get("/region", response_model=RegionOut | None)
async def todays_region(
    session: AsyncSession = SessionDep, visitor: User = Depends(require_visitor)
):
    return await campaign.get_todays_distribution_region(session)


@router.get("/queue", response_model=list[ShopOut])
async def queue(
    session: AsyncSession = SessionDep, visitor: User = Depends(require_visitor)
) -> list:
    """This visitor's slice of today's pack queue — pre-split 50/50 by
    Shop.assigned_subteam when the second sub-team is enabled."""
    return await campaign.get_pack_queue(session, subteam=visitor.visitor_subteam)


@router.post("", response_model=ShopOut)
async def deliver(
    payload: PackDeliveryCreate,
    session: AsyncSession = SessionDep,
    visitor: User = Depends(require_visitor),
):
    try:
        delivery = await campaign.register_pack_delivery(
            session,
            shop_id=payload.shop_id,
            visitor_id=visitor.id,
            opinion_text=payload.opinion_text,
            voice_note_url=payload.voice_note_url,
            score_1_5=payload.score_1_5,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return await session.get(Shop, delivery.shop_id)
