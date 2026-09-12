from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    BTN_NEW_SHOP,
    CANCEL_MENU,
    LOCATION_MENU,
    MAIN_MENU,
    score_keyboard,
)
from app.bot.services import create_shop, get_active_region
from app.bot.states import RegisterShop
from app.models import User

router = Router(name="register")


@router.message(F.text == BTN_NEW_SHOP)
async def start_registration(message: Message, state: FSMContext, session: AsyncSession) -> None:
    region = await get_active_region(session)
    if region is None:
        await message.answer(
            "فعلاً ناحیه‌ی فعالی برای ثبت آدرس تعیین نشده. بعداً دوباره چک کن.",
            reply_markup=MAIN_MENU,
        )
        return

    await state.set_state(RegisterShop.name)
    await state.update_data(region_id=region.id, region_name=region.name)
    await message.answer(
        f"ثبت آدرس جدید برای ناحیه‌ی «{region.name}».\n\nنام فروشگاه رو بفرست:",
        reply_markup=CANCEL_MENU,
    )


@router.message(RegisterShop.name, F.text)
async def got_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(RegisterShop.address)
    await message.answer("آدرس تایپی رو بفرست:", reply_markup=CANCEL_MENU)


@router.message(RegisterShop.address, F.text)
async def got_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(RegisterShop.photo)
    await message.answer("عکس فروشگاه رو بفرست:", reply_markup=CANCEL_MENU)


@router.message(RegisterShop.photo, F.photo)
async def got_photo(message: Message, state: FSMContext) -> None:
    file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=file_id)
    await state.set_state(RegisterShop.score)
    await message.answer(
        "امتیاز احتمال خرید رو انتخاب کن:", reply_markup=score_keyboard("reg_score")
    )


@router.message(RegisterShop.photo)
async def photo_wrong_type(message: Message) -> None:
    await message.answer("لطفاً یک عکس بفرست (نه متن یا فایل دیگه).")


@router.callback_query(RegisterShop.score, F.data.startswith("reg_score:"))
async def got_score(callback: CallbackQuery, state: FSMContext) -> None:
    score = int(callback.data.split(":")[1])
    await state.update_data(score=score)
    await state.set_state(RegisterShop.location)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "حالا لوکیشن مغازه رو با دکمه‌ی زیر ارسال کن:", reply_markup=LOCATION_MENU
    )
    await callback.answer()


@router.message(RegisterShop.location, F.location)
async def got_location(
    message: Message, state: FSMContext, session: AsyncSession, user: User
) -> None:
    data = await state.get_data()
    shop = await create_shop(
        session,
        region_id=data["region_id"],
        registered_by_id=user.id,
        name=data["name"],
        address_text=data["address"],
        photo_file_id=data["photo_file_id"],
        score=data["score"],
        lat=message.location.latitude,
        lng=message.location.longitude,
    )
    await state.clear()
    await message.answer(
        "✅ ثبت شد!\n\n"
        f"فروشگاه: {shop.name}\n"
        f"ناحیه: {data['region_name']}\n"
        f"امتیاز: {'⭐️' * shop.scout_score}\n\n"
        "تا ساعت ۱۸:۰۰ امروز از «ویرایش آدرس‌های امروز» می‌تونی اصلاحش کنی.",
        reply_markup=MAIN_MENU,
    )


@router.message(RegisterShop.location)
async def location_wrong_type(message: Message) -> None:
    await message.answer("برای ادامه، از دکمه‌ی «📍 ارسال لوکیشن» استفاده کن.")
