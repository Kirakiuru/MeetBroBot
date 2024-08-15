from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


kb = [
    [KeyboardButton(text='Navigation Calendar')],
    [KeyboardButton(text='Navigation Calendar w month')],
    [KeyboardButton(text='Dialog Calendar')],
    [KeyboardButton(text='Dialog Calendar w year')],
    [KeyboardButton(text='Dialog Calendar w month')]
]

calendar_type = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
