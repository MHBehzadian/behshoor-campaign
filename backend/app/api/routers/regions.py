from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin, require_staff
from app.api.schemas import RegionCreate, RegionOut, RegionUpdate
from app.models import Region

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionOut], dependencies=[Depends(require_staff)])
async def list_regions(session: AsyncSession = SessionDep) -> list[Region]:
    result = await session.execute(select(Region).order_by(Region.name))
    return list(result.scalars().all())


@router.post("", response_model=RegionOut, dependencies=[Depends(require_admin)])
async def create_region(payload: RegionCreate, session: AsyncSession = SessionDep) -> Region:
    region = Region(**payload.model_dump())
    session.add(region)
    await session.commit()
    await session.refresh(region)
    return region


@router.patch("/{region_id}", response_model=RegionOut, dependencies=[Depends(require_admin)])
async def update_region(
    region_id: int, payload: RegionUpdate, session: AsyncSession = SessionDep
) -> Region:
    region = await session.get(Region, region_id)
    if region is None:
        raise HTTPException(404, "ناحیه پیدا نشد.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(region, field, value)
    await session.commit()
    await session.refresh(region)
    return region
