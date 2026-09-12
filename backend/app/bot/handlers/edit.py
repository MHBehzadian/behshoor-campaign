from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    BTN_EDIT_TODAY,
    CANCEL_MENU,
    FIELD_LABELS,
    LOCATION_MENU,
    MAIN_MENU,
    edit_field_keyboard,
    score_keyboard,
    shop_list_keyboard,
)
from app.bot.services import (
    get_scout_owned_shop,
    get_today_shops_by_scout,
    update_shop_address,
    update_shop_location,
    update_shop_name,
    update_shop_photo,
    update_shop_score,
)
from app.bot.states import EditShop
from app.models import Shop, User

router = Router(name="edit")


def _shop_summary(shop: Shop) -> str:
    return (
        f"📍 <b>{shop.name}</b>\n"
        f"آدرس: {shop.address_text}\n"
        f"امتیاز: {'⭐️' * shop.scout_score}\n\n"
        "کدوم مورد رو ویرایش کنم؟"
    )


@router.message(F.text == BTN_EDIT_TODAY)
async def list_today_shops(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    shops = await get_today_shops_by_scout(session, user.id)
    if not shops:
        await message.answer("امروز هنوز آدرسی ثبت نکردی.", reply_markup=MAIN_MENU)
        return
    await state.set_state(EditShop.choosing_shop)
    await message.answer(
        f"آدرس‌های امروز ({len(shops)} مورد) — یکی رو انتخاب کن:",
        reply_markup=shop_list_keyboard(shops),
    )


@router.callback_query(EditShop.choosing_shop, F.data.startswith("edit_pick:"))
async def pick_shop(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User) -> None:
    shop_id = int(callback.data.split(":")[1])
    shop = await get_scout_owned_shop(session, shop_id, user.id)
    if shop is None:
        await callback.answer("این آدرس پیدا نشد.", show_alert=True)
        return
    await state.update_data(shop_id=shop.id)
    await state.set_state(EditShop.choosing_field)
    await callback.message.edit_text(_shop_summary(shop), reply_markup=edit_field_keyboard(shop.id))
    await callback.answer()


@router.callback_query(EditShop.choosing_field, F.data == "edit_back")
async def back_to_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User) -> None:
    shops = await get_today_shops_by_scout(session, user.id)
    if not shops:
        await state.clear()
        await callback.message.edit_text("امروز هنوز آدرسی ثبت نکردی.")
        await callback.answer()
        return
    await state.set_state(EditShop.choosing_shop)
    await callback.message.edit_text(
        f"آدرس‌های امروز ({len(shops)} مورد) — یکی رو انتخاب کن:",
        reply_markup=shop_list_keyboard(shops),
    )
    await callback.answer()


@router.callback_query(EditShop.choosing_field, F.data.startswith("edit_field:"))
async def choose_field(callback: CallbackQuery, state: FSMContext) -> None:
    _, shop_id, field = callback.data.split(":")
    await state.update_data(shop_id=int(shop_id), field=field)
    label = FIELD_LABELS[field]

    if field == "score":
        await state.set_state(EditShop.score)
        await callback.message.answer(f"مقدار جدید «{label}» رو انتخاب کن:", reply_markup=score_keyboard("edit_score"))
    elif field == "photo":
        await state.set_state(EditShop.photo)
        await callback.message.answer("عکس جدید رو بفرست:", reply_markup=CANCEL_MENU)
    elif field == "location":
        await state.set_state(EditShop.location)
        await callback.message.answer("لوکیشن جدید رو با دکمه‌ی زیر بفرست:", reply_markup=LOCATION_MENU)
    else:
        state_map = {"name": EditShop.name, "address": EditShop.address}
        await state.set_state(state_map[field])
        await callback.message.answer(f"مقدار جدید «{label}» رو بفرست:", reply_markup=CANCEL_MENU)
    await callback.answer()


async def _finish_field_edit(message: Message, state: FSMContext, session: AsyncSession, user: User) -> Shop | None:
    """Common tail for every field-edit handler: fetch the shop being edited,
    verify ownership, and drop back into the field-picker for it."""
    data = await state.get_data()
    shop = await get_scout_owned_shop(session, data["shop_id"], user.id)
    if shop is None:
        await state.clear()
        await message.answer("این آدرس پیدا نشد.", reply_markup=MAIN_MENU)
        return None
    return shop


@router.message(EditShop.name, F.text)
async def edit_name(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    shop = await _finish_field_edit(message, state, session, user)
    if shop is None:
        return
    shop = await update_shop_name(session, shop, message.text.strip())
    await state.set_state(EditShop.choosing_field)
    await message.answer("✅ به‌روزرسانی شد.", reply_markup=edit_field_keyboard(shop.id))


@router.message(EditShop.address, F.text)
async def edit_address(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    shop = await _finish_field_edit(message, state, session, user)
    if shop is None:
        return
    shop = await update_shop_address(session, shop, message.text.strip())
    await state.set_state(EditShop.choosing_field)
    await message.answer("✅ به‌روزرسانی شد.", reply_markup=edit_field_keyboard(shop.id))


@router.message(EditShop.photo, F.photo)
async def edit_photo(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    shop = await _finish_field_edit(message, state, session, user)
    if shop is None:
        return
    shop = await update_shop_photo(session, shop, message.photo[-1].file_id)
    await state.set_state(EditShop.choosing_field)
    await message.answer("✅ به‌روزرسانی شد.", reply_markup=edit_field_keyboard(shop.id))


@router.callback_query(EditShop.score, F.data.startswith("edit_score:"))
async def edit_score(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User) -> None:
    data = await state.get_data()
    shop = await get_scout_owned_shop(session, data["shop_id"], user.id)
    if shop is None:
        await callback.answer("این آدرس پیدا نشد.", show_alert=True)
        return
    score = int(callback.data.split(":")[1])
    shop = await update_shop_score(session, shop, score)
    await state.set_state(EditShop.choosing_field)
    await callback.message.edit_text("✅ به‌روزرسانی شد.", reply_markup=edit_field_keyboard(shop.id))
    await callback.answer()


@router.message(EditShop.location, F.location)
async def edit_location(message: Message, state: FSMContext, session: AsyncSession, user: User) -> None:
    shop = await _finish_field_edit(message, state, session, user)
    if shop is None:
        return
    shop = await update_shop_location(session, shop, message.location.latitude, message.location.longitude)
    await state.set_state(EditShop.choosing_field)
    await message.answer("✅ به‌روزرسانی شد.", reply_markup=edit_field_keyboard(shop.id))
