from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin, require_staff
from app.api.schemas import DayScheduleOut, DayScheduleSet
from app.models import DaySchedule, DayType, User

router = APIRouter(prefix="/day-schedules", tags=["day-schedules"])


@router.get("", response_model=list[DayScheduleOut], dependencies=[Depends(require_staff)])
async def list_day_schedules(
    date_from: date = Query(...),
    date_to: date = Query(...),
    session: AsyncSession = SessionDep,
) -> list[DaySchedule]:
    result = await session.execute(
        select(DaySchedule)
        .where(DaySchedule.date >= date_from, DaySchedule.date <= date_to)
        .order_by(DaySchedule.date)
    )
    return list(result.scalars().all())


@router.put("/{schedule_date}", response_model=DayScheduleOut)
async def set_day_schedule(
    schedule_date: date,
    payload: DayScheduleSet,
    session: AsyncSession = SessionDep,
    admin: User = Depends(require_admin),
) -> DaySchedule:
    """Upsert a single day's type. This is how days get freely rearranged —
    just PUT a new type/region onto whichever date needs it, including
    marking one a holiday."""
    if payload.day_type == DayType.DISTRIBUTION and payload.target_region_id is None:
        raise HTTPException(400, "برای روز پخش باید ناحیه‌ی هدف مشخص شود.")

    result = await session.execute(select(DaySchedule).where(DaySchedule.date == schedule_date))
    schedule = result.scalar_one_or_none()
    target_region_id = payload.target_region_id if payload.day_type == DayType.DISTRIBUTION else None

    if schedule is None:
        schedule = DaySchedule(
            date=schedule_date,
            day_type=payload.day_type,
            target_region_id=target_region_id,
            created_by_id=admin.id,
        )
        session.add(schedule)
    else:
        schedule.day_type = payload.day_type
        schedule.target_region_id = target_region_id

    await session.commit()
    await session.refresh(schedule)
    return schedule
