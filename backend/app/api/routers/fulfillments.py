from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_distributor
from app.api.schemas import OrderFulfillmentCreate, ShopOut
from app.models import Shop, User
from app.services import campaign

router = APIRouter(prefix="/fulfillments", tags=["fulfillments"])


@router.get("/queue", response_model=list[ShopOut])
async def queue(
    session: AsyncSession = SessionDep, distributor: User = Depends(require_distributor)
) -> list[Shop]:
    """Shops whose order (1 or 2) the visitor closed and is now waiting on
    physical delivery + cash collection."""
    return await campaign.get_fulfillment_queue(session)


@router.post("", response_model=ShopOut)
async def fulfill(
    payload: OrderFulfillmentCreate,
    session: AsyncSession = SessionDep,
    distributor: User = Depends(require_distributor),
) -> Shop:
    """The amount entered here is the final source of truth for both this
    distributor's 3% and the visitor's 8% commission."""
    try:
        fulfillment = await campaign.register_order_fulfillment(
            session,
            shop_id=payload.shop_id,
            distributor_id=distributor.id,
            amount=payload.amount,
            notes=payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return await session.get(Shop, fulfillment.shop_id)
