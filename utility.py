from telebot import types


def keyboard(args):
    resize_keyboard = False
    if len(args) < 2:
        resize_keyboard = True

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=resize_keyboard)
    for arg in args:
        btn = types.KeyboardButton(arg)
        markup.add(btn)
    return markup