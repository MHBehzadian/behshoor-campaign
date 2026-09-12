from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_distributor
from app.api.schemas import CheckupComplete, CheckupVisitOut
from app.models import CheckupVisit, User
from app.services import campaign

router = APIRouter(prefix="/checkups", tags=["checkups"])


@router.get("/queue", response_model=list[CheckupVisitOut])
async def queue(
    session: AsyncSession = SessionDep, distributor: User = Depends(require_distributor)
) -> list[CheckupVisit]:
    """This distributor's weekly check-ups on steady customers, due today."""
    return await campaign.get_checkup_queue(session, distributor.id)


@router.post("/{checkup_id}/complete", response_model=CheckupVisitOut)
async def complete(
    checkup_id: int,
    payload: CheckupComplete,
    session: AsyncSession = SessionDep,
    distributor: User = Depends(require_distributor),
) -> CheckupVisit:
    """Logging the visit also schedules the next one automatically, and — if
    a reorder amount is given — records it and the distributor's 3% (no
    visitor cut on these; steady-customer reorders are distributor-only)."""
    try:
        return await campaign.complete_checkup(
            session,
            checkup_id=checkup_id,
            distributor_id=distributor.id,
            method=payload.method,
            notes=payload.notes,
            resulted_order_amount=payload.resulted_order_amount,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
