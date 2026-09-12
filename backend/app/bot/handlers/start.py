from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards import BTN_CANCEL, MAIN_MENU
from app.models import User

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await message.answer(
        f"سلام {user.full_name} 👋\n"
        "این بات برای ثبت آدرس مغازه‌هاست. از منو یکی رو انتخاب کن:",
        reply_markup=MAIN_MENU,
    )


@router.message(StateFilter("*"), Command("cancel"))
@router.message(StateFilter("*"), F.text == BTN_CANCEL)
async def cancel_anything(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("لغو شد.", reply_markup=MAIN_MENU)
