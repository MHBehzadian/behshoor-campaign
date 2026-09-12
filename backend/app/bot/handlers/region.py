from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import BTN_ACTIVE_REGION, MAIN_MENU
from app.bot.services import get_active_region

router = Router(name="region")


@router.message(F.text == BTN_ACTIVE_REGION)
async def show_active_region(message: Message, session: AsyncSession) -> None:
    region = await get_active_region(session)
    if region is None:
        await message.answer(
            "فعلاً ناحیه‌ی فعالی برای ثبت آدرس تعیین نشده. بعداً دوباره چک کن.",
            reply_markup=MAIN_MENU,
        )
        return

    caption = f"🗺 ناحیه‌ی فعال: <b>{region.name}</b>\n\nآدرس‌ها رو به‌ترتیب، کوچه به کوچه، برای همین ناحیه ثبت کن."
    if region.reference_photo_url:
        await message.answer_photo(region.reference_photo_url, caption=caption, reply_markup=MAIN_MENU)
    else:
        await message.answer(caption, reply_markup=MAIN_MENU)
