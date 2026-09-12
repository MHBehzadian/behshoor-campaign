from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin
from app.api.schemas import SettingsOut, SettingsUpdate
from app.models import Settings, User
from app.services.common import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut, dependencies=[Depends(require_admin)])
async def read_settings(session: AsyncSession = SessionDep) -> Settings:
    return await get_settings(session)


@router.patch("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    session: AsyncSession = SessionDep,
    admin: User = Depends(require_admin),
) -> Settings:
    settings = await get_settings(session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await session.commit()
    await session.refresh(settings)
    return settings
