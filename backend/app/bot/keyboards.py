from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app.models import Shop

BTN_NEW_SHOP = "📍 ثبت آدرس جدید"
BTN_EDIT_TODAY = "✏️ ویرایش آدرس‌های امروز"
BTN_ACTIVE_REGION = "🗺 ناحیه‌ی فعال"
BTN_CANCEL = "❌ انصراف"
BTN_SEND_LOCATION = "📍 ارسال لوکیشن"

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_NEW_SHOP)],
        [KeyboardButton(text=BTN_EDIT_TODAY)],
        [KeyboardButton(text=BTN_ACTIVE_REGION)],
    ],
    resize_keyboard=True,
)

CANCEL_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
    resize_keyboard=True,
)

LOCATION_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_SEND_LOCATION, request_location=True)],
        [KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)

NO_KEYBOARD = ReplyKeyboardRemove()

FIELD_LABELS = {
    "name": "نام فروشگاه",
    "address": "آدرس",
    "photo": "عکس",
    "score": "امتیاز",
    "location": "لوکیشن",
}


def score_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️ ۱", callback_data=f"{callback_prefix}:1"),
                InlineKeyboardButton(text="⭐️⭐️ ۲", callback_data=f"{callback_prefix}:2"),
                InlineKeyboardButton(text="⭐️⭐️⭐️ ۳", callback_data=f"{callback_prefix}:3"),
            ]
        ]
    )


def shop_list_keyboard(shops: list[Shop]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{i+1}. {shop.name}", callback_data=f"edit_pick:{shop.id}")]
        for i, shop in enumerate(shops)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_field_keyboard(shop_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"✏️ {label}", callback_data=f"edit_field:{shop_id}:{key}")]
        for key, label in FIELD_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="⬅️ بازگشت به لیست", callback_data="edit_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
