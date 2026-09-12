from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin
from app.api.schemas import UserCreate, UserOut
from app.models import User, UserRole
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[UserOut])
async def list_users(session: AsyncSession = SessionDep) -> list[User]:
    result = await session.execute(select(User).order_by(User.role, User.full_name))
    return list(result.scalars().all())


@router.post("", response_model=UserOut)
async def create_user(payload: UserCreate, session: AsyncSession = SessionDep) -> User:
    if payload.role == UserRole.SCOUT and not payload.telegram_id:
        raise HTTPException(400, "برای در‌آور، آیدی تلگرام لازم است.")
    if payload.role != UserRole.SCOUT and not (payload.username and payload.password):
        raise HTTPException(400, "برای ورود به وب‌سایت، کاربری و رمز لازم است.")

    user = User(
        role=payload.role,
        full_name=payload.full_name,
        phone=payload.phone,
        telegram_id=payload.telegram_id,
        username=payload.username,
        password_hash=hash_password(payload.password) if payload.password else None,
        visitor_subteam=payload.visitor_subteam,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
