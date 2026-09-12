from aiogram.fsm.state import State, StatesGroup


class RegisterShop(StatesGroup):
    name = State()
    address = State()
    photo = State()
    score = State()
    location = State()


class EditShop(StatesGroup):
    choosing_shop = State()
    choosing_field = State()
    name = State()
    address = State()
    photo = State()
    score = State()
    location = State()
