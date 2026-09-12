from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User, UserRole
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SessionDep = Depends(get_session)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = SessionDep,
) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "ورود نامعتبر است.")
    user_id = decode_access_token(token)
    if user_id is None:
        raise unauthorized
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user


def require_role(*roles: UserRole) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "دسترسی نداری.")
        return user

    return checker


require_admin = require_role(UserRole.ADMIN)
require_visitor = require_role(UserRole.VISITOR)
require_distributor = require_role(UserRole.DISTRIBUTOR)
require_staff = require_role(UserRole.ADMIN, UserRole.VISITOR, UserRole.DISTRIBUTOR)
