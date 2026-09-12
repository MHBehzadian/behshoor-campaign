from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.db import async_session
from app.models import User, UserRole

ALLOWED_ROLES = (UserRole.SCOUT, UserRole.ADMIN)  # website roles never touch the bot


class AuthMiddleware(BaseMiddleware):
    """Register on dp.message and dp.callback_query separately so `event` is
    always a concrete Message/CallbackQuery with `.answer()`."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        async with async_session() as session:
            result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
            user = result.scalar_one_or_none()

        if user is None or not user.is_active or user.role not in ALLOWED_ROLES:
            denial = "⛔️ شما به این بات دسترسی ندارید. با ادمین تماس بگیرید."
            if isinstance(event, CallbackQuery):
                await event.answer(denial, show_alert=True)
            else:
                await event.answer(denial)
            return None

        data["user"] = user
        return await handler(event, data)


class DbSessionMiddleware(BaseMiddleware):
    """Injects a fresh AsyncSession as data['session'] for every update,
    scoped to that single update's handling."""

    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
