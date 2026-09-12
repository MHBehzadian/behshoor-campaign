from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_visitor
from app.api.schemas import FollowUpAttemptCreate, ShopOut
from app.models import Shop, User
from app.services import campaign

router = APIRouter(prefix="/followups", tags=["followups"])


@router.get("/queue", response_model=list[ShopOut])
async def queue(
    session: AsyncSession = SessionDep, visitor: User = Depends(require_visitor)
) -> list[Shop]:
    """Shops due for a follow-up visit today (order 1 or order 2 — the
    current status on each shop tells you which)."""
    return await campaign.get_followup_queue(session)


@router.post("", response_model=ShopOut)
async def attempt(
    payload: FollowUpAttemptCreate,
    session: AsyncSession = SessionDep,
    visitor: User = Depends(require_visitor),
) -> Shop:
    if payload.closed and not payload.product_name:
        raise HTTPException(400, "برای بستن سفارش، نام محصول لازم است.")
    try:
        result = await campaign.register_followup_attempt(
            session,
            shop_id=payload.shop_id,
            visitor_id=visitor.id,
            closed=payload.closed,
            product_name=payload.product_name,
            reject_reason=payload.reject_reason,
            rescheduled_to=payload.rescheduled_to,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return await session.get(Shop, result.shop_id)
