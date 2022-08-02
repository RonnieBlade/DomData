import asyncio
import collections
import random
import re
import time

from telebot import types

from static_data import random_belarus_stickers

import myfiles
from translater import t

special_topics_dic = myfiles.open_categories('special_topics.txt')


def keyboard(args):
    resize_keyboard = False
    if len(args) < 2:
        resize_keyboard = True

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=resize_keyboard)
    for arg in args:
        btn = types.KeyboardButton(arg)
        markup.add(btn)
    return markup


def create_demo_house(user, msg, step_new_house_func, new_item_func, update_item_attribute_func, send_msg_txt_func, add_highlighted_thing_func, dom):

    if user.busy:
        return

    user.busy = True

    send_msg_txt_func(user.id, t('dd_demo_house', user))
    time.sleep(0.5)
    send_msg_txt_func(user.id, "⏳")

    house = step_new_house_func(user, t('dd_house', user), auto=True, demo_role='house', has_img=True)
    user.step.location = house.id

    send_msg_txt_func(user.id, t('dd_example', user))

    asyncio.run(update_item_attribute_func(user, msg, "comment", t('dd_house_comment', user), auto=True))

    level2 = new_item_func(user, t('dd_level_2', user), "level", "level", "signal_strength", auto=True)

    user.step.location = level2.id
    room1 = new_item_func(user, t('dd_bedroom', user), "room", "room", "door", auto=True, demo_role='bedroom')

    user.step.location = house.id
    room2 = new_item_func(user, t('dd_lounge', user), "room", "room", "door", auto=True, demo_role='livingroom')
    garage = new_item_func(user, t('dd_garage', user), "room", "room", "door", auto=True, demo_role='garage')

    user.step.location = room1.id

    # bed appears in the current location
    bed = new_item_func(user, t('dd_bed', user), "item", "etc", "bed", auto=True)
    closet = new_item_func(user, t('dd_closet', user), "cupboard", "cupboard", "file_cabinet", auto=True)

    user.step.location = closet.id

    # appears in the current location
    book = new_item_func(user, t('dd_book', user), "item", "paper", "book", auto=True, demo_role='book')

    # appears in the current location
    photoalbum = new_item_func(user, t('dd_photoalbum', user), "item", "paper", "notebook", auto=True,
                               demo_role='photoalbum')

    send_msg_txt_func(user.id, t('dd_click_on_id', user))

    user.step.location = room2.id
    cabinet = new_item_func(user, t('dd_cabinet', user), "cupboard", "cupboard", "file_cabinet", auto=True)
    bob = new_item_func(user, t('dd_bobmarley', user), "item", "infocarrier", "cd", auto=True, demo_role='bobmarley')
    user.step.location = bob.id
    asyncio.run(update_item_attribute_func(user, msg, "comment", t('dd_bob_comment', user), auto=True))

    user.step.location = cabinet.id

    left_drawer = new_item_func(user, t('dd_left_drawer', user), "storage", "storage", "black_square_button", auto=True)
    right_drawer = new_item_func(user, t('dd_right_drawer', user), "storage", "storage", "black_square_button", auto=True)

    # appears in the current location
    recordplayer = new_item_func(user, t('dd_recordplayer', user), "item", "tech", None, auto=True, demo_role='recordplayer')
    radio = new_item_func(user, t('dd_radio', user), "item", "tech", "radio", auto=True, demo_role='radio')
    user.step.location = radio.id
    asyncio.run(update_item_attribute_func(user, msg, "comment", t('dd_repair', user), auto=True))
    asyncio.run(update_item_attribute_func(user, msg, "highlighted_by", 1))
    add_highlighted_thing_func(radio, user, dom)

    user.step.location = left_drawer.id

    # appears in the current location
    eyeglasses = new_item_func(user, t('dd_eyeglasses', user), "item", "clothes", "eyeglasses", auto=True,
                               demo_role='shades')

    send_msg_txt_func(user.id, t('dd_almost_ready', user))

    box = new_item_func(user, t('dd_box', user), "box", "box", "package", auto=True)
    user.step.location = box.id

    # appears in the current location
    art = new_item_func(user, t('dd_art', user), "item", "etc", "art", auto=True, demo_role='arttools')

    user.step.location = right_drawer.id

    # appears in the current location
    gun = new_item_func(user, t('dd_gun', user), "item", "etc", "gun", auto=True, demo_role='watergun')

    user.step.location = garage.id

    # appears in the current location
    car = new_item_func(user, t('dd_car', user), "item", "etc", "oncoming_automobile", auto=True, demo_role='car')

    msg.text = f"/{user.id_conv(house.id)}"

    user.step.name = "main_menu"

    user.busy = False


def special_words_check(telegram_id, msg, send_msg_txt_func):

    # Working with stickers
    if msg.text is None:
        if msg.sticker is not None:
            if 'wrw' in special_topics_dic.keys():
                if msg.sticker.set_name.lower() in special_topics_dic['wrw']:
                    send_msg_txt_func(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
                    myfiles.save_request_to_file(telegram_id, 'sticker', ('conversation_logs', 'special_topics.log'))
                    return True
        return False

    # Working with text
    found = False

    if 'wrw' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['wrw']):
            send_msg_txt_func(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
            myfiles.save_request_to_file(telegram_id, 'flag', ('conversation_logs', 'special_topics.log'))
            found = True

    if 'belarus' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['belarus']):
            send_msg_txt_func(telegram_id, "Жыве вечна!", remove_keyboard=False)
            time.sleep(1)
            send_msg_txt_func(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
            myfiles.save_request_to_file(telegram_id, msg.text, ('conversation_logs', 'special_topics.log'))
            found = True

    if 'ukraine' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['ukraine']):
            send_msg_txt_func(telegram_id, "Героям слава!", remove_keyboard=False)
            time.sleep(1)
            myfiles.save_request_to_file(telegram_id, msg.text, ('conversation_logs', 'special_topics.log'))
            found = True

    if 'censored' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['censored']):
            send_msg_txt_func(telegram_id, "🙈", remove_keyboard=False)
            myfiles.save_request_to_file(telegram_id, msg.text, ('conversation_logs', 'censored.log'))
            found = True

    if 'humiliation' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['humiliation']):
            send_msg_txt_func(telegram_id, 'CAACAgIAAxkBAAIWHl_hIO765r2tvb0KFSjENVvhJc5VAAJZAAOELrgGmubs-nA_1bseBA', False,
                         True,
                         remove_keyboard=False)
            myfiles.save_request_to_file(telegram_id, msg.text, ('conversation_logs', 'humiliation.log'))
            found = True

    return found


def filter_text(txt, max_len=128):
    txt = re.sub(r'[^a-zA-Zа-яА-Я0-9-.,:;\'’() ёЁ]', '', txt)
    if len(txt) > max_len:
        txt = txt[:max_len]
    return txt


def close_tags(txt):
    tags = ['*', '_', '`']

    for tag in tags:
        if txt.count(tag) % 2 != 0:
            last_char_index = txt.rfind(tag)
            txt = txt[:last_char_index] + "" + txt[last_char_index + 1:]

    txt.replace('[', '')
    txt.replace(']', '')

    return txt


def get_emoji_chart(emojis, top=10):
    counter = collections.Counter(emojis)
    res = counter.most_common(top)
    fin_res = ""
    for r in res:
        fin_res += r[0]
    return fin_res