from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin
from app.api.schemas import CommissionEntryOut
from app.models import CommissionLedger

router = APIRouter(prefix="/commissions", tags=["commissions"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[CommissionEntryOut])
async def list_commissions(
    user_id: int | None = None,
    session: AsyncSession = SessionDep,
) -> list[CommissionLedger]:
    query = select(CommissionLedger)
    if user_id is not None:
        query = query.where(CommissionLedger.user_id == user_id)
    result = await session.execute(query.order_by(CommissionLedger.computed_at.desc()))
    return list(result.scalars().all())
