from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, get_current_user
from app.api.schemas import LoginRequest, MeResponse, TokenResponse
from app.models import User, UserRole
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

WEBSITE_ROLES = (UserRole.ADMIN, UserRole.VISITOR, UserRole.DISTRIBUTOR)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = SessionDep) -> TokenResponse:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "نام کاربری یا رمز اشتباه است.")
    result = await session.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if (
        user is None
        or user.role not in WEBSITE_ROLES
        or not user.is_active
        or not user.password_hash
        or not verify_password(payload.password, user.password_hash)
    ):
        raise invalid
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
