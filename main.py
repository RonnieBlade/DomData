import copy
import os
import random
import re
import telebot
import ftper
import myfiles
import time
from telebot import types
from mydom import *
from translater import *
import randtext as rt
from mysearch import compare
import imagga_API
import collections
import datetime

import threading
from config_reader import read_config

devs = read_config("config.ini", "developers")['developers'].split(',')
devs = list(map(int, devs))

teletoken = 'token'

testing_mode = True

if testing_mode:
    # testing bot
    teletoken = 'token_test'

all_item_fields = "id, name, location, type, last_move_date, dom_id, item_class, item_emoji, user_id, has_img, tags, file_id, taken_by_user, last_taken_date, comment, commented_by_user, comment_date, wish_status, wished_by_user, wish_date, purchased_by_user, purchase_date, highlighted_by, highlighted_date, tagged_by, tags_date, demo_role"

tags_count = 50

logger = mylogger.get_logger(__name__)

# if testing_mode: token_test
# else: token
token = read_config("config.ini", "telegram")[teletoken]
bot = telebot.TeleBot(token)

user_loading_lock = threading.Lock()

dom = []
ibase = AllItemsList()

# all languages
allowed_languages = {"en", "ru"}

# all users online
users = set()


def step_start(user, msg):
    go_to_about(user, msg)
    time.sleep(3)

    if user.lang is None:
        go_to_change_lang(user, msg)
        return
    elif user.name is None:
        go_to_change_name(user, msg)
        return
    else:
        go_to_main_menu(user, msg, False)


def go_top_level(user, msg):
    msg.text = "0"
    go_to_main_menu(user, msg, False)


def go_to_delete_img(user, msg):
    location = find_item_by_id(user.step.location, dom, user)
    if location is not None:
        user.step.name = "delete_img"
        reply = f"{t('do_you_want_to_delete_pic', user)} \"{location.name}\"?"
        send_msg_txt_and_keyboard(user.id, reply, keyboard(t("yes_no_keyboard", user)))
    else:
        send_msg_txt(user.id, t('cant_take_pic', user))
        previous_step(user, msg)


def go_to_change_img(user, msg):
    go_to_add_img(user, msg)


def go_to_add_img(user, msg):
    location = find_item_by_id(user.step.location, dom, user)
    if location is not None:

        if not limits_ok(user, msg, 'new_img', status='request'):
            return

        if location.type == 'item':
            if not limits_ok(user, msg, 'imagga', status='request'):
                return

        user.step.name = "add_img"
        send_msg_txt(user.id, f"{t('take_pic', user)} \"{location.name}\" {t('or_cancel', user)}")
    else:
        send_msg_txt(user.id, t('cant_take_pic', user), remove_keyboard=False)


def go_to_change_emoji(user, msg):
    item_to_change_emoji = find_item_by_id(user.step.location, dom, user)
    if item_to_change_emoji is None or item_to_change_emoji.type != "item":
        send_msg_txt(user.id, t("cant_change_class", user))
        previous_step(user, msg)
        return

    go_to_new_item_class(user, msg, True)


def go_to_search_by_class_or_emoji(user, msg):
    go_to_new_item_class(user, msg, False, True)


def go_to_search_by_name(user, msg):
    user.step.name = "search_by_name"
    l = find_item_by_id(user.step.location, dom, user)
    n_l = "/DomData"
    if l is not None:

        user.update_dic(l.id)

        # Minimum search area - house
        h = list(
            filter(lambda r: r.dom_id == l.dom_id and r.type == "dom", dom))
        if len(h) != 0:
            l = h[0]

        e_l = ""
        if l.item_emoji is not None:
            e_l = " " + l.item_emoji
        n_l = f"/{user.id_conv(l.id)} {l.name}{e_l}"

    r = f"{t('search_in', user)} {n_l}:\n{t('search_by_name', user)}"
    send_msg_txt(user.id, r)


def go_to_comment(user, msg):
    if user.step.location == 0:
        send_msg_txt(user.id, t("cant_comment_root", user))
        previous_step(user, msg)
        return

    item = find_item_by_id(user.step.location, dom, user)

    if item is None:
        send_msg_txt(user.id, f"{t('cant_find', user)} {user.step.location}")
        previous_step(user, msg)
        return

    user.step.name = "comment_item"
    del_comment_line = ""
    if item.comment is not None and item.comment != "":
        send_msg_txt(user.id, f"{item.comment}")
        del_comment_line = f" {t('or_del_comment', user)}"
    send_msg_txt(user.id, f"{t('comment_step', user)}{del_comment_line}")


def go_to_rename_item(user, msg):
    if user.step.location == 0:
        send_msg_txt(user.id, t("cant_rename_root", user))
        previous_step(user, msg)
        return

    item = find_item_by_id(user.step.location, dom, user)

    if item is None:
        send_msg_txt(user.id, f"{t('cant_find', user)} {user.step.location}")
        previous_step(user, msg)
        return

    item_emoji = ""
    if item.item_emoji is not None:
        item_emoji = item.item_emoji + " "

    user.step.name = "rename_item"
    if item.name is not None and item.name != "":
        send_msg_txt(user.id, f"{item.name}")
    send_msg_txt(user.id, f"{t('rename', user)}")


def limits_ok(user, msg, atype='user_msg', content=None, status='request'):
    ok = user.new_action(atype, content, status)
    if not ok:
        if user.premium:
            send_msg_txt(user.id, t("too_many_requests_premium", user))
        else:
            send_msg_txt(user.id, t("too_many_requests", user))
        time.sleep(5)
        previous_step(user, msg)
        return False
    return True


def go_to_new_house(user, msg):
    if not limits_ok(user, msg, 'new_house', status='request'):
        return
    user.step.name = "new_house"
    send_msg_txt(user.id, t("new_house", user))


def go_to_share_access_add(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None:
        send_msg_txt(user.id, t("access_denied", user))
        return

    if location.user_id != user.id:
        send_msg_txt(user.id, t("access_denied", user))
        return

    user.step.name = "share_access_add"
    send_msg_txt(user.id, t("enter_id_to_share", user))


def go_to_share_access(user, msg):
    user.step.name = "share_access"

    this_house = find_item_by_id(user.step.location, dom, user)

    if this_house is None:
        send_msg_txt(user.id, t("cant_share", user))
        previous_step(user, msg)
        return

    dom_key = mydb.get_dom_access_key(this_house.dom_id)

    user.step.sharing_access_key = dom_key

    user_ids_with_key = mydb.get_user_ids_having_the_key(dom_key)

    users_objs = mydb.get_users(user_ids_with_key)

    users_txt = ""

    for id in user_ids_with_key:
        u = next((x for x in users_objs if x.id == id), None)
        if u is not None:
            if u.id == this_house.user_id:
                users_txt += f"*id{id}* {u.name} ({t('creator', user)})\n"
            else:
                users_txt += f"/denyid{id} {u.name}"
                if u.id == user.id:
                    users_txt += f" ({t('share_access_remove_yourself', user)})\n"
                users_txt += "\n"
        else:
            users_txt += f"/denyid{id}\n"

    my_keyboard = [t('but_back', user)]

    deny_line = ""
    if user.id == this_house.user_id:
        if len(user_ids_with_key) > 1:
            deny_line = f"\n_{t('to_deny_access', user)}_"
        my_keyboard.insert(0, t('share_access_but_add', user))

    reply = f"{t('access_list', user)} \"{this_house.name}\":\n{users_txt}{deny_line}"
    send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard))


def go_to_new_level(user, msg):
    if not limits_ok(user, msg, 'new_item', status='request'):
        return

    user.step.name = "new_level"
    send_msg_txt(user.id, t("new_level", user))


def go_to_new_room(user, msg):
    if not limits_ok(user, msg, 'new_item', status='request'):
        return

    user.step.name = "new_room"
    send_msg_txt(user.id, t("new_room", user))


def go_to_new_item_name(user, msg, item_class='item'):
    user.step.name = "new_item"
    send_msg_txt(user.id, t(f"new_{item_class}", user))


def go_to_new_item(user, msg):
    if not limits_ok(user, msg, 'new_item', status='request'):
        return

    go_to_new_item_type(user, msg)


def go_to_search(user, msg):
    user.step.name = "search"
    reply = t('search_type', user)
    send_msg_txt_and_keyboard(user.id, reply, keyboard(t("search_keyboard", user)))


def go_to_put_back(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0 or location.taken_by_user is None:
        send_msg_txt(user.id, t("already_here", user))
    else:
        location.taken_by_user = None
        remove_missing_thing(location, user, dom)
        update_item_attribute(user, msg, "taken_by_user", None)

    previous_step(user, msg)


def go_to_unhighlight(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0 or location.highlighted_by is None:
        send_msg_txt(user.id, t("already_here", user))
    else:
        location.highlighted_by = None
        remove_highlighted_thing(location, user, dom)
        update_item_attribute(user, msg, "highlighted_by", None)

    previous_step(user, msg)


def get_it_back(user, msg):
    if user.item_in_hands is None:
        send_msg_txt(user.id, t("nothing_in_my_hands", user))
        previous_step(user, msg)
        return

    location = find_item_by_id(user.item_in_hands.location, dom, user)

    if location is None or user.step.location == 0:
        send_msg_txt(user.id, t("cant_put", user))
        previous_step(user, msg)
        return

    location.space.append(user.item_in_hands)

    user.item_in_hands = None
    user.item_in_hands_put_but_text = None
    user.step.location = location.id
    previous_step(user, msg)


def put_it_here(user, msg):
    if user.item_in_hands is None:
        send_msg_txt(user.id, t("nothing_in_my_hands", user))
        previous_step(user, msg)
        return

    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0:
        send_msg_txt(user.id, t("cant_put", user))
        previous_step(user, msg)
        return

    #good_place_to_land = can_i_put_it_here(location.type, user.item_in_hands.type)
    good_place_to_land = location.can_i_put_it_here(user.item_in_hands)

    if not good_place_to_land:
        send_msg_txt(user.id, t("cant_put", user))
        previous_step(user, msg)
        return

    if user.item_in_hands.highlighted_by is not None:
        remove_highlighted_thing(user.item_in_hands, user, dom)
    if user.item_in_hands.taken_by_user is not None:
        remove_missing_thing(user.item_in_hands, user, dom)

    user.item_in_hands.location = location.id
    user.item_in_hands.dom_id = location.dom_id
    location.space.append(user.item_in_hands)

    if user.item_in_hands.highlighted_by is not None:
        add_highlighted_thing(user.item_in_hands, user, dom)
    if user.item_in_hands.taken_by_user is not None:
        add_missing_thing(user.item_in_hands, user, dom)

    update_item_attribute(user, msg, "location", location.id)
    update_item_attribute(user, msg, "dom_id", location.dom_id)

    user.item_in_hands = None
    user.item_in_hands_put_but_text = None

    user.last_put_item_location = location

    previous_step(user, msg)


def go_to_delete_item(user, msg):
    item = find_item_by_id(user.step.location, dom, user)

    if item is None:
        send_msg_txt(user.id, t("cant_delete", user), remove_keyboard=False)
        return

    if item.dom_id not in user.houses:
        send_msg_txt(user.id, t("access_denied", user))
        return

    if item.type in {"dom", "house"} and item.user_id != user.id:
        send_msg_txt(user.id, t("access_denied", user))
        return

    if len(item.space) > 0:
        send_msg_txt(user.id, t("can_delete_empty_only", user), remove_keyboard=False)
        return

    user.step.name = "delete_item"

    item_class_str = ""
    if item.item_class is not None and item.item_class != '':
        item_class_str = f" ({t(item.item_class, user).lower()})"

    reply = f"{t('do_you_want_to_delete', user)} \"{item.name}\"{item_class_str}?"
    send_msg_txt_and_keyboard(user.id, reply, keyboard(t("yes_no_keyboard", user)))


def go_to_highlight(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0:
        send_msg_txt(user.id, t("cant_highlight", user))
        previous_step(user, msg)
        return

    if location.type not in {"item", "box", "storage", "cupboard"}:
        send_msg_txt(user.id, t("cant_highlight", user))
        previous_step(user, msg)
        return

    location.highlighted_by = user.id
    update_item_attribute(user, msg, "highlighted_by", user.id)
    add_highlighted_thing(location, user, dom)
    previous_step(user, msg)


def go_to_take_to_use(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    if location.type not in {"item", "box"}:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    parent = find_item_by_id(location.location, dom, user)

    if parent is None:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    location.taken_by_user = user.id
    update_item_attribute(user, msg, "taken_by_user", user.id)
    add_missing_thing(location, user, dom)
    previous_step(user, msg)


def go_to_take_item(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None or user.step.location == 0 or location.taken_by_user is not None:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    if location.type in {"dom", "house"}:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    parent = find_item_by_id(location.location, dom, user)

    if parent is None:
        send_msg_txt(user.id, t("cant_take", user))
        previous_step(user, msg)
        return

    took_from = find_item_by_id(location.location, dom, user)

    user.last_take_item_location = took_from

    user.item_in_hands = location
    parent.space.remove(location)
    user.step.location = parent.id
    previous_step(user, msg)


def go_to_new_item_type(user, msg):
    user.step.name = "new_item_type"

    keyboard_type = "new_item_type_keyboard"

    location = find_item_by_id(user.step.location, dom, user)

    if location is None:
        previous_step(user, msg)
        return

    if location.type in {"cupboard", "storage"}:
        keyboard_type = "new_item_type_in_cupboard_keyboard"
    elif location.type == "box":
        keyboard_type = "new_item_type_in_box_keyboard"
    elif location.type == "item":
        user.step.new_item_type = "item"
        go_to_new_item_name(user, msg)
        return

    reply = t("new_item_type", user)
    send_msg_txt_and_keyboard(user.id, reply, keyboard(t(keyboard_type, user)))


def guess_class_and_emoji(user, msg):
    img_res = []

    str_res = search_item_by_part_of_name(user.step.new_item_name, ibase.values, 3, True, True)

    if user.step.new_item_with_photo:
        img_res = search_item_by_photo(user.step.new_item_tags, ibase.values, 1000, True)
        for r in img_res:
            r.update({'total_dist': r['min_dist'] / 100})

    str_res = sort_results_by_words_and_full_distance(str_res, user.step.new_item_name, 10)

    all_res = str_res + img_res
    all_res = sorted(all_res, key=lambda r: r['total_dist'], reverse=False)

    emojies = []

    for r in all_res:
        # both the class and the emoji must be selected, although only the class can be selected, but then the user
        # may not see that the program has set the wrong class
        # the total_dist limit used to be no more than 8, now it is more strict, no more than zero
        if r['total_dist'] <= 0 and r['item'].item_emoji is not None:

            if r['item'].item_class is not None:
                user.step.new_item_class = r['item'].item_class

            if r['item'].item_emoji is not None and len(emojies) < 10:
                emojies.append(r['item'].item_emoji)

    if len(emojies) == 0:
        return False

    em = emoji_chart(emojies, 1)

    em = emoji.demojize(em, use_aliases=True)
    em = em.replace(':', "")
    user.step.new_item_emoji = em

    return True


def go_to_new_item_class(user, msg, update=False, search=False):
    if not update and not search and user.step.new_item_type != "item":
        new_item(user, user.step.new_item_name, user.step.new_item_type, user.step.new_item_class,
                 user.step.new_item_emoji_str)
        return

    if not update and not search:
        sure = guess_class_and_emoji(user, msg)
        if sure:
            new_item(user, user.step.new_item_name, user.step.new_item_type, user.step.new_item_class,
                     user.step.new_item_emoji)
            return

    reply = t("new_item_class", user)

    if update:
        user.step.name = "new_item_class_update"
        reply = t("new_item_class_update", user)
    elif search:
        user.step.name = "search_by_class"
        reply = t("search_by_item_class", user)
    else:
        user.step.name = "new_item_class"

    send_msg_txt_and_keyboard(user.id, reply, keyboard(t("new_item_class_keyboard", user)))


def go_to_new_item_emoji(user, msg, update=False, search=False):
    user.step.name = "new_item_emoji"

    reply = t("new_item_emoji", user)

    if update:
        user.step.name = "new_item_emoji_update"
        reply = t("new_item_emoji_update", user)
    if search:
        user.step.name = "search_by_emoji"
        reply = t("search_by_item_emoji", user)

    if search:
        emoji_keyboard = [t("go_back", user), t("any", user)]
    else:
        emoji_keyboard = [t("go_back", user), t("no_emoji", user)]

    emoji_keyboard.extend(emoji_dic.get(user.step.new_item_class))

    send_msg_txt_and_keyboard(user.id, reply, keyboard(emoji_keyboard))


def get_user_name(user_id):
    if user_id == 1:
        return 'DomData'

    user = find_or_create_user(user_id, users, True)
    if user.name is not None:
        return user.name
    else:
        return f"id{user_id}"


def get_user_houses(user):
    keys = mydb.get_user_keys(user.id)
    houses = mydb.get_user_houses(keys)
    return houses


def go_to_main_menu(user, msg, reload=True):
    if user.loading:
        return

    if reload:
        send_msg_txt(user.id, t('wait', user))
        send_msg_txt(user.id, "⏳")
        get_items(user, dom)

    user.step.name = "main_menu"

    dir = get_dir(0, dom, user)
    dir_str = show_dir(dir, dom, user, True)

    user.step.location = 0

    if user.premium:
        version = ' ⭐️'
    else:
        version = ''

    reply = f"/DomData\n{t('my_profile', user)}: {user.name} id{user.id}{version}\n\n{dir_str}"
    send_item_to_user(user, reply, "top")


def create_demo_house(user, msg, first_time=False):
    if first_time:
        time.sleep(1)
    else:
        if not limits_ok(user, msg, 'demo_house', status='request'):
            return
        user.new_action('demo_house', status='complete')

    if user.busy:
        return

    user.busy = True

    send_msg_txt(user.id, t('dd_demo_house', user))
    time.sleep(0.5)
    send_msg_txt(user.id, "⏳")

    house = step_new_house(user, t('dd_house', user), auto=True, demo_role='house', has_img=True)
    user.step.location = house.id

    send_msg_txt(user.id, t('dd_example', user))

    update_item_attribute(user, msg, "comment", t('dd_house_comment', user), auto=True)

    level2 = new_item(user, t('dd_level_2', user), "level", "level", "signal_strength", auto=True)

    user.step.location = level2.id
    room1 = new_item(user, t('dd_bedroom', user), "room", "room", "door", auto=True, demo_role='bedroom')

    user.step.location = house.id
    room2 = new_item(user, t('dd_lounge', user), "room", "room", "door", auto=True, demo_role='livingroom')
    garage = new_item(user, t('dd_garage', user), "room", "room", "door", auto=True, demo_role='garage')

    user.step.location = room1.id

    # bed appears in the current location
    bed = new_item(user, t('dd_bed', user), "item", "etc", "bed", auto=True)
    closet = new_item(user, t('dd_closet', user), "cupboard", "cupboard", "file_cabinet", auto=True)

    user.step.location = closet.id

    # appears in the current location
    book = new_item(user, t('dd_book', user), "item", "paper", "book", auto=True, demo_role='book')

    # appears in the current location
    photoalbum = new_item(user, t('dd_photoalbum', user), "item", "paper", "notebook", auto=True,
                          demo_role='photoalbum')

    send_msg_txt(user.id, t('dd_click_on_id', user))

    user.step.location = room2.id
    cabinet = new_item(user, t('dd_cabinet', user), "cupboard", "cupboard", "file_cabinet", auto=True)
    bob = new_item(user, t('dd_bobmarley', user), "item", "infocarrier", "cd", auto=True, demo_role='bobmarley')
    user.step.location = bob.id
    update_item_attribute(user, msg, "comment", t('dd_bob_comment', user), auto=True)

    user.step.location = cabinet.id

    left_drawer = new_item(user, t('dd_left_drawer', user), "storage", "storage", "black_square_button", auto=True)
    right_drawer = new_item(user, t('dd_right_drawer', user), "storage", "storage", "black_square_button", auto=True)

    # appears in the current location
    recordplayer = new_item(user, t('dd_recordplayer', user), "item", "tech", None, auto=True, demo_role='recordplayer')
    radio = new_item(user, t('dd_radio', user), "item", "tech", "radio", auto=True, demo_role='radio')
    user.step.location = radio.id
    update_item_attribute(user, msg, "comment", t('dd_repair', user), auto=True)
    update_item_attribute(user, msg, "highlighted_by", 1)
    radio.highlighted_by = 1
    add_highlighted_thing(radio, user, dom)

    user.step.location = left_drawer.id

    # appears in the current location
    eyeglasses = new_item(user, t('dd_eyeglasses', user), "item", "clothes", "eyeglasses", auto=True,
                          demo_role='shades')

    send_msg_txt(user.id, t('dd_almost_ready', user))

    box = new_item(user, t('dd_box', user), "box", "box", "package", auto=True)
    user.step.location = box.id

    # appears in the current location
    art = new_item(user, t('dd_art', user), "item", "etc", "art", auto=True, demo_role='arttools')

    user.step.location = right_drawer.id

    # appears in the current location
    gun = new_item(user, t('dd_gun', user), "item", "etc", "gun", auto=True, demo_role='watergun')

    user.step.location = garage.id

    # appears in the current location
    car = new_item(user, t('dd_car', user), "item", "etc", "oncoming_automobile", auto=True, demo_role='car')

    msg.text = f"/{user.id_conv(house.id)}"

    user.step.name = "main_menu"

    user.busy = False

    # if not first_time:
    go_to_item(user, msg)


def send_item_to_user(user, reply, keyboard_type="item", similar_obj=False, similar_object_id=False):
    if similar_obj:
        location = find_item_by_id(similar_object_id, dom, user)
    else:
        location = find_item_by_id(user.step.location, dom, user)

    my_keyboard = []

    img = False

    if location is not None and location.has_img:
        img = location.id

        if location.demo_role is not None:
            img = location.demo_role

    add_take_but = False
    add_take_to_use_but = False
    add_put_back_but = False
    commented = False
    highlighted = False

    if location is not None and location.comment is not None:
        commented = True
    if location is not None and location.highlighted_by is not None:
        highlighted = True

    if keyboard_type != "top":

        if keyboard_type in {"item", "box"}:
            if location.taken_by_user is None:
                add_take_to_use_but = True
            else:
                my_keyboard.insert(-1, t('put_back', user))
                add_put_back_but = True

        if keyboard_type in {"dom", "house"}:
            my_keyboard.insert(0, t('go_up_house', user))
        elif keyboard_type == "level":
            my_keyboard.insert(0, t('go_up_level', user))
        else:
            my_keyboard.insert(0, t('go_up', user))

        if user.item_in_hands is None:
            if keyboard_type not in {"dom", "house"} and not add_put_back_but:
                add_take_but = True
        else:
            if location is not None and location.type is not None and location.taken_by_user is None:
                if location.can_i_put_it_here(user.item_in_hands):
                    if user.item_in_hands.item_class is not None:
                        item_class_txt = f" ({t(user.item_in_hands.item_class, user).lower()})"
                    else:
                        item_class_txt = ""
                    if location.item_class is not None:
                        location_item_class_txt = f" ({t(location.item_class, user).lower()})"
                    else:
                        location_item_class_txt = ""
                    but_txt = f"{t('put', user)} \"{user.item_in_hands.name}\"{item_class_txt} {t('in', user)} {location.name}{location_item_class_txt}"
                    user.item_in_hands_put_but_text = but_txt
                    my_keyboard.append(but_txt)

    if keyboard_type in {"box", "storage", "cupboard", "item"}:

        if keyboard_type == "item":
            my_keyboard.extend(t("item_keyboard", user))
        if keyboard_type == "box":
            my_keyboard.extend(t("box_keyboard", user))
        if keyboard_type == "storage":
            my_keyboard.extend(t("storage_keyboard", user))
        if keyboard_type == "cupboard":
            my_keyboard.extend(t("cupboard_keyboard", user))

        if keyboard_type == "item":
            take_but_order = 1
        elif keyboard_type == "box":
            take_but_order = 2
        else:
            take_but_order = -2
        if add_take_but:
            my_keyboard.insert(take_but_order, t(f'take_{keyboard_type}', user))

        if location.has_img:
            my_keyboard.insert(-3, t('change_img', user))
            my_keyboard.insert(-3, t('delete_img', user))
        else:
            my_keyboard.insert(-3, t('add_img', user))

        if add_take_to_use_but:
            my_keyboard.insert(-3, t('take_to_use', user))

        if commented:
            my_keyboard.insert(-3, t('edit_comment', user))
        else:
            my_keyboard.insert(-3, t('comment', user))

        if highlighted:
            my_keyboard.insert(-3, t('dehighlight', user))
        else:
            my_keyboard.insert(-3, t('highlight', user))

        if similar_obj:
            sim_o = f"{t('similar_object', user)} \"{location.name}\" {t('already_exists', user)}\n"
            reply = sim_o + reply
            my_keyboard = t('yes_no_keyboard', user)

        send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard), img, location)
    elif keyboard_type == "top":
        my_keyboard.extend(t("main_menu_keyboard", user))

        if len(user.houses) > 0:
            my_keyboard.insert(0, t('search', user))

        send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard))
    elif keyboard_type in {"dom", "house"}:

        my_keyboard.extend(t("house_keyboard", user))

        if len(location.space) > 0:
            my_keyboard.insert(1, t('search', user))

        if location.user_id == user.id:
            my_keyboard.append(t('delete_house_but', user))

        if commented:
            my_keyboard.insert(-2, t('edit_comment', user))
        else:
            my_keyboard.insert(-2, t('comment', user))

        if location.has_img:
            my_keyboard.insert(-3, t('change_img', user))
            my_keyboard.insert(-1, t('delete_img', user))
        else:
            my_keyboard.insert(-3, t('add_img', user))

        send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard), img, location)
    elif keyboard_type == "level":

        my_keyboard.extend(t("level_keyboard", user))

        if location.has_img:
            my_keyboard.insert(-4, t('change_img', user))
            my_keyboard.insert(-3, t('delete_img', user))
        else:
            my_keyboard.insert(-4, t('add_img', user))

        if commented:
            my_keyboard.insert(-4, t('edit_comment', user))
        else:
            my_keyboard.insert(-4, t('comment', user))

        if add_take_but:
            my_keyboard.insert(-3, t('take_level', user))

        send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard), img, location)
    elif keyboard_type == "room":

        my_keyboard.extend(t("room_keyboard", user))

        if location.has_img:
            my_keyboard.insert(-4, t('change_img', user))
            my_keyboard.insert(-3, t('delete_img', user))
        else:
            my_keyboard.insert(-4, t('add_img', user))

        if add_take_but:
            my_keyboard.insert(-3, t('take_room', user))

        send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard), img, location)
    else:
        send_msg_txt(user.id, f"{reply}")


def go_to_help(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help", user), keyboard(t("help_keyboard", user)))


def help_tutorial(user, msg, no_keyboard=False):
    if no_keyboard:
        send_msg_txt(user.id, t("video_tutorial", user), remove_keyboard=True)
    else:
        # close_tags=False because there is an underscore in the video address, there is no such option that the text
        # can be with an underscore
        send_msg_txt_and_keyboard(user.id, t("video_tutorial", user), keyboard(t("help_keyboard_back", user)),
                                  must_close_tags=False)


def help_about(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_about", user), keyboard(t("help_keyboard_back", user)))


def help_basics(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_basics", user), keyboard(t("help_keyboard_back", user)))


def help_navigation(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_navigation", user), keyboard(t("help_keyboard_back", user)))


def help_premium(user, msg):
    if isinstance(user, User) and user.premium:
        send_msg_txt_and_keyboard(user.id, t("help_premium_subscribed", user), keyboard(t("help_keyboard_back", user)))
    else:
        send_msg_txt_and_keyboard(user.id, t("help_premium", user), keyboard(t("help_keyboard_back", user)))


def help_keyboard(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_nokeyboard", user), keyboard(t("help_keyboard_back", user)))


def help_location(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_location", user), keyboard(t("help_keyboard_back", user)))


def help_conception(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_conception", user), keyboard(t("help_keyboard_back", user)))


def help_search(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_search", user), keyboard(t("help_keyboard_back", user)))


def help_access(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_access", user), keyboard(t("help_keyboard_back", user)))


def help_security(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_security", user), keyboard(t("help_keyboard_back", user)))


def help_privacy(user, msg):
    send_msg_txt_and_keyboard(user.id, t("help_privacy", user), keyboard(t("help_keyboard_back", user)))


def go_to_about(user, msg, startup=False):
    ctype = 'about'
    if startup:
        ctype = 'about_startup'
    send_msg_txt(user.id, t(ctype, user), remove_keyboard=startup)


def go_to_offer_demo(user, msg):
    user.step.name = 'offer_demo'
    send_msg_txt_and_keyboard(user.id, t('offer_demo', user), keyboard(t('offer_demo_keyboard', user)))


def go_to_change_lang(user, msg, first_start=False):
    user.step.name = "lang_choice"

    typ = "choose_lang"

    if first_start:
        user.step.name = "lang_choice_first"
        typ = "choose_lang_first"

    send_msg_txt_and_keyboard(user.id, t(typ, user), keyboard(["English", "Русский"]))


def go_to_change_name(user, msg):
    user.step.name = "change_name"
    send_msg_txt(user.id, t("whats_your_name", user))


def go_up(user, msg):
    item = find_item_by_id(user.step.location, dom, user)

    if item is None:
        send_msg_txt(user.id, f"{t('cant_find', user)}", remove_keyboard=False)
        time.sleep(1)
        previous_step(user, msg)
        return

    dir = get_dir(item.location, dom, user)
    top = False
    if dir is not None and dir.type == "top":
        go_top_level(user, msg)
        return
        # stop here
        top = True
    user.step.location = dir.id
    dir_txt = show_dir(dir, dom, user, top)
    keyboard_type = dir.type
    send_item_to_user(user, dir_txt, keyboard_type)


def save_request_to_file(user, txt, file_path):
    if isinstance(user, User) and user.name is not None:
        user_str = f"{user.name} ({user.id})"
    else:
        user_str = f"User {user}"

    with open(file_path, "a", encoding="utf-8") as f:
        now = datetime.datetime.now().strftime("%Y.%m.%d, %H:%M:%S")
        f.write(f"{now} {user_str}:\n{txt}\n\n")


def go_to_item(user, msg):
    txt = msg.text
    if str(txt).startswith("/"):
        txt = txt[1:]

    dir = get_dir(txt, dom, user, True)
    top = False
    if dir is not None and dir.type == "top":
        top = True

    if dir is None:
        send_msg_txt(user.id, f"{t('cant_find', user)} \"{msg.text}\" {t('try_search', user)}", remove_keyboard=False)
        save_request_to_file(user, txt, os.path.join('conversation_logs', 'failed_requests.log'))
        time.sleep(1)
        previous_step(user, msg)
        return

    user.step.location = dir.id
    dir_txt = show_dir(dir, dom, user, top)

    keyboard_type = dir.type

    send_item_to_user(user, dir_txt, keyboard_type)


def step_main_menu(user, msg):
    func = user_commands.get(msg.text)

    if func is None:
        go_to_item(user, msg)
        return

    func(user, msg)


def step_new_level(user, msg):
    if if_canceled(user, msg):
        return

    level_name = filter_text(msg.text)
    new_item(user, level_name, "level", "level", "signal_strength")


def step_new_room(user, msg):
    if if_canceled(user, msg):
        return

    room_name = filter_text(msg.text)
    new_item(user, room_name, "room", "room", "door")


def previous_step(user, msg, go_top=False):
    location = user.step.location
    if go_top:
        location = 0

    user.step = Step("main_menu", location)
    msg.text = user.id_conv(location)

    if location == 0:
        msg.text = "/DomData"

    step_main_menu(user, msg)


def if_canceled(user, msg):
    if msg.text in {"/cancel", "Cancel", "Отмена"}:
        previous_step(user, msg)
        return True
    else:
        return False


def delete_item_photo_ftp(user, item_id):
    pic_name = f"item_{item_id}"
    ftp_success = ftper.upload_img(None, pic_name, True)

    if not ftp_success:
        send_msg_txt(user.id, "Can't delete the file")
        return False
    return True


def add_item_photo_ftp(user, item_id):
    temp_pic_name = f"temp_pic_user{user.id}"
    pic_name = f"item_{item_id}"
    ftp_success = ftper.upload_img(temp_pic_name, pic_name)

    if not ftp_success:
        send_msg_txt(user.id, t("cant_upload_img", user))
        return False

    myfiles.delete_temp_pic(temp_pic_name)
    return True


def tags_prepare(tags, count):
    if tags is None:
        return None
    new_tags = tags[:count]
    new_tags_new_format = []
    for t in new_tags:
        tag = {"c": round(t.get("confidence"), 2), "tag": t.get("tag").get("en")}
        new_tags_new_format.append(tag)
    return new_tags_new_format


def save_photo_and_get_tags(user, msg, new_item=False, search=False, resolution=400):
    send_msg_txt(user.id, "⏳")

    user.new_action('new_img', status='complete')

    temp_pic_name = f"temp_pic_user{user.id}"

    file_saved = myfiles.save_pic(msg, temp_pic_name, bot, True, resolution)
    if not file_saved:
        send_msg_txt(user.id, "❌")
        return False

    location = find_item_by_id(user.step.location, dom, user)

    if location is not None and location.item_class not in {"house", "dom", "level", "room", 'cupboard', 'storage',
                                                            'box'} or (
            new_item and user.step.new_item_type == "item") or search:
        user.new_action('imagga', status='complete')
        tags = imagga_API.get_image_tags(user, f'images/{temp_pic_name}.jpg')

        if tags is None:
            send_msg_to_developer(f'Imagga refused to respond:\nUser: {user.name} {user.id}')

    else:
        tags = None

    return tags


def new_item_with_photo(user, msg):
    if user.step.new_item_type == 'item':
        resolution = 400
        if user.premium:
            resolution = 600
    else:
        resolution = 600
        if user.premium:
            resolution = 800

    tags = save_photo_and_get_tags(user, msg, True, resolution=resolution)

    if tags is None and user.step.new_item_type == 'item':
        send_msg_txt(msg, t("cant_upload_img", user), True)
        return

    user.step.temp_item_tags = tags
    user.step.new_item_tags = tags_prepare(tags, tags_count)
    user.step.new_item_with_photo = True

    if msg.caption is not None:
        new_name = filter_text(msg.caption)
        if len(new_name) >= 3:
            user.step.new_item_name = msg.caption

    location = find_item_by_id(user.step.location, dom, user)
    house_list = list(
        filter(lambda r: r.dom_id == location.dom_id, dom))
    if len(house_list) != 0:
        search_area = house_list
    else:
        search_area = dom

    res = search_item_by_photo(user.step.new_item_tags, search_area, 300)

    if len(res) != 0:
        res = sorted(res, key=lambda r: r['min_dist'], reverse=False)
        user.step.name = "similar_object"
        sim_o = find_item_by_id(res[0]['item'].id, dom, user)
        dir_txt = show_dir(sim_o, dom, user, False)
        send_item_to_user(user, dir_txt, "item", True, sim_o.id)
        return

    if msg.caption is not None or user.step.new_item_type != 'item':
        if user.step.new_item_type != 'item':
            user.step.new_item_name = t(user.step.new_item_type, user)
        go_to_new_item_class(user, msg)
        return

    offer_user_name_variants(user, msg, tags)


def offer_user_name_variants(user, msg, tags):
    reply = t("choose_name_from_tags", user)

    tags = tags[:10]
    my_keyboard = []
    for tag in tags:
        but = tag.get("tag").get(user.lang)
        if but not in my_keyboard:
            my_keyboard.append(but)

    my_keyboard.append(t("cancel", user))
    send_msg_txt_and_keyboard(user.id, reply, keyboard(my_keyboard))

    user.step.name = "new_item"


def clear_new_item_info(user):
    user.step.new_item_name = ""
    user.step.new_item_type = ""
    user.step.new_item_class = ""
    user.step.new_item_with_photo = False
    user.step.new_item_tags = []
    user.step.temp_item_tags = []
    user.step.new_item_emoji_str = ""


def step_similar_object(user, msg):
    if msg.text in {"Yes", "Да"}:
        if user.step.new_item_name is not None and user.step.new_item_name != "":
            step_new_item(user, msg)
        else:
            offer_user_name_variants(user, msg, user.step.temp_item_tags)
    elif msg.text in {"No", "Нет"}:
        clear_new_item_info(user)
        go_to_new_item_name(user, msg)
    else:
        user.step.name = "main_menu"
        go_to_item(user, msg)


def step_new_item(user, msg):
    if if_canceled(user, msg):
        clear_new_item_info(user)
        return

    if msg.text is not None and msg.text != "" and msg.text.startswith('/'):
        user.step = Step("main_menu", user.step.location)
        go_to_item(user, msg)
        return

    if msg.content_type == "photo":
        new_item_with_photo(user, msg)
        return

    new_name = filter_text(msg.text)

    if len(new_name) < 3 and len(user.step.new_item_name) < 3:
        send_msg_txt(user.id, t('name_is_too_short', user), remove_keyboard=False)
        return

    if user.step.new_item_name == "":
        user.step.new_item_name = new_name
    go_to_new_item_class(user, msg)


def step_new_item_type(user, msg):
    if if_canceled(user, msg):
        return

    type_str = item_types_dic.get(msg.text)
    if type_str is None:
        user.step.new_item_type = "item"
        step_new_item(user, msg)
        # by default let's assume that the user wants to create an item
        return

    user.step.new_item_type = type_str

    if type_str != "item":
        if type_str == "cupboard":
            user.step.new_item_class = "cupboard"
            user.step.new_item_emoji_str = "file_cabinet"
        elif type_str == "storage":
            user.step.new_item_class = "storage"
            user.step.new_item_emoji_str = "black_square_button"
        elif type_str == "box":
            user.step.new_item_class = "box"
            user.step.new_item_emoji_str = "package"

    go_to_new_item_name(user, msg, item_class=type_str)


def step_new_item_class_update(user, msg):
    step_new_item_class(user, msg, True)


def step_new_item_class(user, msg, update=False, search=False):
    if if_canceled(user, msg):
        clear_new_item_info(user)
        return
    class_str = item_classes_dic.get(msg.text)
    if class_str is None:
        send_msg_txt(msg, t("class_doesnt_exist", user), True)
        go_to_new_item_class(user, msg, update, search)
        return
    user.step.new_item_class = class_str
    go_to_new_item_emoji(user, msg, update, search)


def step_new_item_emoji_update(user, msg):
    step_new_item_emoji(user, msg, True)


def step_new_item_emoji(user, msg, update=False, search=False):
    emoji_str = emoji.demojize(msg.text, use_aliases=True)

    if emoji_str in {"Go back", "Назад", "/go_back", "/back"}:
        go_to_new_item_class(user, msg, update, search)
        return

    # if there is a command "No emoji" - then remove the emoji, if not, then remove the colon from the line
    if emoji_str in {"No emoji", "Без emoji", "/noemoji", "/no_emoji", "Any", "Любой"}:
        emoji_str = None
    else:

        if emoji_str == msg.text:
            send_msg_txt(user.id, t("choose_emoji_from_list", user), remove_keyboard=False)
            return

        emoji_str = emoji_str.replace(":", "")

    if update:
        update_item_attribute(user, msg, "item_class", user.step.new_item_class)
        update_item_attribute(user, msg, "item_emoji", emoji_str)
        previous_step(user, msg)
    elif search:
        if emoji_str is None:
            msg.text = user.step.new_item_class
            step_search_by_name(user, msg, True, False)
        else:
            step_search_by_name(user, msg, False, True)
    else:
        new_item(user, user.step.new_item_name, user.step.new_item_type, user.step.new_item_class, emoji_str)


def new_item(user, name, my_type, item_class, item_emoji=None, auto=False, demo_role=None):
    has_img = user.step.new_item_with_photo
    tags = user.step.new_item_tags

    if demo_role is not None:
        has_img = True

        if my_type == 'item':
            user_for_tags_english_only = copy.deepcopy(user)
            user_for_tags_english_only.lang = 'en'
            tags_str = t(f'dd_{demo_role}_tags', user_for_tags_english_only)
            tags_str = tags_str.replace("'", "\"")
            tags = json.loads(tags_str)

    if not auto:
        user.new_action('new_item', content=name, status='complete')

    location = user.step.location
    parent = find_item_by_id(location, dom, user)
    id_int = \
        mydb.add_item(parent.dom_id, location, name, my_type, user.id, item_class, item_emoji, has_img, tags,
                      demo_role)[0]
    item = Item(id_int, name, location, my_type, datetime.datetime.now(), parent.dom_id, item_class, item_emoji,
                user.id, has_img, tags, demo_role=demo_role)
    parent.space.append(item)

    user.update_dic(id_int)

    if user.step.new_item_with_photo and not auto:
        suc = add_item_photo_ftp(user, id_int)
        if not suc:
            send_msg_txt(user.id, t("cant_upload_img", user), True)

    ibase.append(item)

    current_dir = get_dir(parent.id, dom, user)
    current_dir_txt = show_dir(current_dir, dom, user, False)

    if not auto:
        user.step = Step("main_menu", parent.id)
        send_item_to_user(user, current_dir_txt, parent.type)

    return item


def go_to_change_item_emoji(user, msg):
    if if_canceled(user, msg):
        return

    new_name = filter_text(msg.text)

    update_item_attribute(user, msg, "name", new_name)
    previous_step(user, msg)


def deny_house_access(user, msg):
    location = find_item_by_id(user.step.location, dom, user)

    if location is None:
        send_msg_txt(user.id, t("access_denied", user))
        return

    if not msg.text.startswith("/denyid"):
        send_msg_txt(user.id, t('dont_understand', user))
        go_to_share_access(user, msg)
        return

    step_share_access_add(user, msg, True)


def step_share_access_add(user, msg, deleting=False):
    if msg.text in {"/cancel", "Cancel"}:
        go_to_share_access(user, msg)
        return

    id_txt = re.sub(r'[^0-9’]', '', msg.text)

    location = find_item_by_id(user.step.location, dom, user)

    id_int = 0

    try:
        id_int = int(id_txt)
    except ValueError as err:
        logger.error(err)
        send_msg_txt(user.id, t('dont_understand', user), remove_keyboard=False)
        return

    if user.step.sharing_access_key is None:
        send_msg_txt(user.id, t('no_access_key', user))
        go_to_share_access(user, msg)
        return

    user_to_share = User(id_int)

    if deleting:
        mydb.delete_access_key(user_to_share, user.step.sharing_access_key)
        send_msg_txt(user.id, f"{t('access_denied_for_user', user)} id{id_txt}")
    else:
        mydb.add_access_key(user_to_share, user.step.sharing_access_key)
        send_msg_txt(user.id, f"{t('shared_with', user)} {id_txt}")

    working_user = next((x for x in users if x.id == id_int), None)

    if working_user is not None:
        get_items(working_user, dom)
        if not deleting and user.name is not None:
            send_msg_txt(id_int, f"{user.name} {t('shared_with_you', user)} \"{location.name}\" /DomData")

    # if the user has denied access to himself
    if deleting and user_to_share.id == user.id:
        user.step.sharing_access_key = None
        previous_step(user, msg, True)
    else:
        go_to_share_access(user, msg)


def step_search_by_class(user, msg):
    step_new_item_class(user, msg, False, True)


def step_search_by_emoji(user, msg):
    step_new_item_emoji(user, msg, False, True)


def step_search_by_name(user, msg, search_by_class=False, search_by_emoji=False):
    search_by_photo = False

    if msg.content_type == "photo":
        search_by_photo = True

    if msg.text == "/cancel":
        previous_step(user, msg)
        return
    if msg.text == "/search_by_class":
        go_to_search_by_class_or_emoji(user, msg)
        return
    if msg.text == "/settings":
        go_to_search(user, msg)
        return

    if msg.text is not None and msg.text.startswith("/"):
        user.step.name = "main_menu"
        go_to_item(user, msg)
        return

    # emoji in name query test
    if not search_by_emoji and not search_by_photo and len(msg.text) != 0:
        text_demojize = emoji.demojize(msg.text, use_aliases=True)
        if text_demojize != msg.text:
            pattern = r":[a-z_]+:"
            smiles = re.findall(pattern, text_demojize)
            if len(smiles) > 0:
                msg.text = emoji.emojize(smiles[0], use_aliases=True)
                step_search_by_name(user, msg, False, True)
                return

    if search_by_photo:
        tags = save_photo_and_get_tags(user, msg, True, search=True)

        if tags is None:
            send_msg_txt(msg, t("cant_upload_img", user), True)
            go_to_search(user, msg)
            return

        s_query = tags_prepare(tags, tags_count)
    elif not search_by_class and not search_by_emoji and not search_by_photo:
        s_query = filter_text(msg.text)
    else:
        s_query = msg.text

    if s_query is None:
        s_query = ""

    if len(s_query) < 3 and not search_by_class and not search_by_emoji and not search_by_photo:
        send_msg_txt(msg, t('query_is_too_short', user), True)
        go_to_search_by_name(user, msg)
        return

    # minimum search area - house
    location = find_item_by_id(user.step.location, dom, user)
    if location is not None:
        h = list(
            filter(lambda r: r.dom_id == location.dom_id and r.type == "dom", dom))
        if len(h) != 0:
            location = h[0]

    if location is None:
        filtered_items = list(dom)
        filtered_items = list(filter(lambda item: item.dom_id in user.houses, filtered_items))
        location = Item(0, f"{t('my_doms', user)}", -1, "top", datetime.datetime.now(), 0, None, None, 0, None, None,
                        None, filtered_items)

    path = find_item_path(user, location, dom, True, True)

    if search_by_photo:
        res = search_item_by_photo(s_query, location.space, 1000)
    elif search_by_class:
        res = search_item_by_class_or_emoji(s_query, location.space)
    elif search_by_emoji:
        res = search_item_by_class_or_emoji(s_query, location.space, True)
    else:
        res = search_item_by_part_of_name(s_query, location.space, 3)

    all_results = sorted(res, key=lambda r: r['min_dist'], reverse=False)

    if not search_by_class and not search_by_emoji and not search_by_photo:
        all_results = sort_results_by_words_and_full_distance(all_results, s_query, 15)

    if not search_by_class and not search_by_emoji:
        all_results = all_results[:10]

    res_txt = ""

    for rr in all_results:
        user.update_dic(rr['item'].id)
        r_path_lines = (find_item_path(user, rr['item'], dom, False, False, False)).splitlines()

        if len(r_path_lines) > 3:
            r_path_lines = r_path_lines[1:]
        if len(r_path_lines) > 5:
            r_path_lines.insert(1, "...")
            while len(r_path_lines) > 4:
                r_path_lines.pop(2)

        r_path_str = ' → '.join(r_path_lines)

        item_emoji_str = ""
        if rr['item'].item_emoji is not None:
            item_emoji_str = rr['item'].item_emoji + " "

        res_txt += f"\n/{user.id_conv(rr['item'].id)} {item_emoji_str}*{rr['item'].name}* ➡️{r_path_str}\n"

    res_txt = res_txt[:-1]

    if len(all_results) == 0:
        res_txt = f"\n{t('nothing_found', user)}"

    request_txt = f"{t('for', user)} \"{s_query}\""
    if search_by_class:
        request_txt = f"{t('for_class', user)} {t(s_query, user)}"
    if search_by_emoji:
        request_txt = f"{t('for_emoji', user)} {s_query}"
    if search_by_photo:
        request_txt = f"{t('for_photo', user)}"

    reply = f"{path}\n\n{t('search_results', user)} {request_txt}:\n{res_txt}"

    send_msg_txt(user.id, reply)
    time.sleep(1)
    go_to_search_by_name(user, msg)


def step_search(user, msg):
    if msg.text in {"Back", "Назад"}:
        previous_step(user, msg)
    elif msg.text in {"Search by name", "Поиск по названию"}:
        go_to_search_by_name(user, msg)
    elif msg.text in {"Search by class or emoji", "Поиск по классу или эмодзи", "/search_by_class"}:
        go_to_search_by_class_or_emoji(user, msg)
    else:
        send_msg_txt(user.id, t('dont_understand', user))


def step_share_access(user, msg):
    if msg.text in {"Back", "Назад", "/cancel"}:
        previous_step(user, msg)
    elif msg.text in {"Add user", "Добавить пользователя"}:
        go_to_share_access_add(user, msg)
    else:
        deny_house_access(user, msg)


def step_delete_img(user, msg):
    if msg.text in {"Yes", "Да"}:
        item = find_item_by_id(user.step.location, dom, user)
        suc = delete_item_photo_ftp(user, item.id)

        if not suc:
            send_msg_txt(user.id, t("cant_delete_img", user), True)
            previous_step(user, msg)
            return

        update_item_attribute(user, msg, "has_img", False)
        if item.demo_role is not None:
            update_item_attribute(user, msg, "demo_role", False)
        # Also, need to remove image tags... Searching by img can still find the item, bug or feature?

    previous_step(user, msg)


def step_delete_item(user, msg):
    if msg.text in {"Yes", "Да"}:
        item = find_item_by_id(user.step.location, dom, user)
        remove_missing_thing(item, user, dom)
        remove_highlighted_thing(item, user, dom)
        delete_item(user, msg, item, dom)
    else:
        previous_step(user, msg)


def get_appropriate_resolution(user, msg):
    if user.step.new_item_type == 'item':
        resolution = 400
        if user.premium:
            resolution = 720
    else:
        resolution = 600
        if user.premium:
            resolution = 900

    return resolution


def step_add_img(user, msg):
    if if_canceled(user, msg):
        return

    if msg.content_type != "photo":
        go_to_add_img(user, msg)
        return

    resolution = get_appropriate_resolution(user, msg)

    tags = save_photo_and_get_tags(user, msg, resolution=resolution)

    if tags is False:
        send_msg_txt(msg, t("cant_upload_img", user), True)
        go_to_add_img(user, msg)
        return

    new_item_tags = tags_prepare(tags, 20)

    item = find_item_by_id(user.step.location, dom, user)
    if item is not None:
        item.tags = new_item_tags
        item.file_id = None

    if tags is not None:
        new_item_tags = json.dumps(new_item_tags)
    else:
        new_item_tags = None

    upload_suc = add_item_photo_ftp(user, user.step.location)

    if upload_suc:
        update_item_attribute(user, msg, "has_img", True)
        update_item_attribute(user, msg, "tags", new_item_tags)
        update_item_attribute(user, msg, "file_id", None, True, item)

        update_item_attribute(user, msg, "tagged_by", user.id)
        update_item_attribute(user, msg, "tags_date", datetime.datetime.now())

        if item.demo_role is not None:
            update_item_attribute(user, msg, "demo_role", None)

    previous_step(user, msg)


def step_comment_item(user, msg):
    if if_canceled(user, msg):
        return

    if msg.text == "/deleteComment":
        new_comment = None
    else:
        new_comment = filter_text(msg.text, 512)

    if new_comment is not None and len(new_comment) < 3:
        send_msg_txt(user.id, t('comment_is_too_short', user), remove_keyboard=False)
        return

    update_item_attribute(user, msg, "comment", new_comment)
    previous_step(user, msg)


def step_rename_item(user, msg):
    if if_canceled(user, msg):
        return

    new_name = filter_text(msg.text)

    if len(new_name) < 3:
        send_msg_txt(user.id, t('name_is_too_short', user), remove_keyboard=False)
        return

    update_item_attribute(user, msg, "name", new_name)
    previous_step(user, msg)


def delete_item(user, msg, item, items):
    ta = threading.Thread(target=lambda: mydb.delete_item(item.id))
    ta.start()

    if item.type in {"house", "dom"}:
        mydb.delete_dom_and_key(item.dom_id)

    item_class_str = ""
    if item.item_class is not None and item.item_class != '':
        item_class_str = f" ({t(item.item_class, user).lower()})"

    send_msg_txt(user.id, f"{t('object', user)} \"{item.name}\"{item_class_str} {t('deleted', user)}")

    parent = find_item_by_id(item.location, dom, user)
    if parent is None:
        parent = dom
        # it means we are on the top level, it has no list "space"
        dom.remove(item)

        ibase.remove_by_id(item.id)

        user.step.location = 0
    else:
        parent.space.remove(item)

        ibase.remove_by_id(item.id)

        user.step.location = parent.id

    previous_step(user, msg)


def update_item_attribute(user, msg, atr, value, change_file_id=False, change_file_id_item=False, auto=False):
    if not change_file_id:
        item = find_item_by_id(user.step.location, dom, user)
    else:
        item = change_file_id_item

    if item is None:
        send_msg_txt(user.id, f"{t('cant_find', user)} {user.step.location}")
        previous_step(user, msg)
        return

    # Usually we change the attribute of the place (item, room, etc) where we are now,
    # but when we change the location attribute we modify the item that user is "holding in his hands"
    if atr in {"location", "dom_id"}:
        item = user.item_in_hands

    ta = threading.Thread(target=lambda: mydb.update_item("dom", "id", atr, value, item.id))
    ta.start()

    reply = ""

    if atr == "demo_role":
        # no reply needed
        return
    if atr == "file_id":
        # no reply needed
        return
    if atr == "tags":
        # no reply needed
        return
    if atr == "tagged_by":
        # no reply needed
        return
    if atr == "tags_date":
        # no reply needed
        return
    if atr == "dom_id":
        # no reply needed
        return
    if atr == "location":
        item.date = datetime.datetime.now()
        ta = threading.Thread(target=lambda: mydb.update_item("dom", "id", "last_move_date", item.date, item.id))
        ta.start()
        # no reply needed
        return
    if atr == "taken_by_user":
        item.last_taken_date = datetime.datetime.now()
        ta = threading.Thread(
            target=lambda: mydb.update_item("dom", "id", "last_taken_date", item.last_taken_date, item.id))
        ta.start()
        # no reply needed
        return
    if atr == "highlighted_by":
        item.highlighted_date = datetime.datetime.now()
        ta = threading.Thread(
            target=lambda: mydb.update_item("dom", "id", "highlighted_date", item.highlighted_date, item.id))
        ta.start()
        # no reply needed
        return
    if atr == "has_img":
        item.has_img = value
        if value:
            reply = f"{t('pic_of', user)} *{item.name}* {t('is_uploaded', user)}"
        else:
            reply = f"{t('pic_of', user)} *{item.name}* {t('is_deleted', user)}"
    elif atr == "name":
        if item.type in {"house", "dom"}:
            ta = threading.Thread(target=lambda: mydb.update_item("doms", "id", atr, value, item.dom_id))
            ta.start()
        old_name = item.name
        item.name = value
        reply = f"*{old_name}* {t('renamed_to', user)} *{value}*"
    elif atr == "comment":

        item.comment = value
        item.commented_by_user = user.id

        if auto:
            item.commented_by_user = 1

        item.comment_date = datetime.datetime.now()
        ta = threading.Thread(
            target=lambda: mydb.update_item("dom", "id", "commented_by_user", item.commented_by_user, item.id))
        ta.start()
        ta2 = threading.Thread(target=lambda: mydb.update_item("dom", "id", "comment_date", item.comment_date, item.id))
        ta2.start()

        if not auto:
            if value is None:
                reply = f"{t('item_comment_deleted', user)}"
            else:
                reply = f"{t('the_object', user)} *{item.name}* {t('item_commented', user)}"
        else:
            return

    elif atr == "item_class":

        if item.item_class is not None:
            old_class_str = item.item_class
            if value == old_class_str:
                reply = f"{t('class_remains', user)} *{t(value, user).lower()}*"
            else:
                reply = f"{t('class_changed', user)} {t('from', user)} *{t(old_class_str, user).lower()}* {t('to', user)} *{t(value, user).lower()}*"
        else:
            reply = f"{t('class_changed', user)} {t('to', user)} *{t(value, user).lower()}*"
        item.item_class = value
    elif atr == "item_emoji":
        new_emoji = emoji.emojize(f":{value}:", use_aliases=True)
        if value is None or value == "None":
            new_emoji = None
            reply = f"{t('emoji_removed', user)}"
        else:
            if item.item_emoji is not None:
                old_emoji_str = item.item_emoji
                reply = f"{t('emoji_changed', user)} {t('from', user)} {old_emoji_str} {t('to', user)} {new_emoji}"
            else:
                reply = f"{t('emoji_changed', user)} {t('to', user)} {new_emoji}"
        item.item_emoji = new_emoji

    send_msg_txt(user.id, reply)


def step_new_house(user, msg, auto=False, demo_role=None, has_img=False):
    if not auto and if_canceled(user, msg):
        return

    if auto:
        dom_name = msg
    else:
        dom_name = msg.text

    house_name = filter_text(dom_name)

    if len(house_name) < 3:
        send_msg_txt(user.id, t('name_is_too_short', user), remove_keyboard=False)
        return

    if not auto:
        user.new_action('new_house', 'complete')
        send_msg_txt(user.id, "⏳")
        user.busy = True

    key = get_and_add_unique_key(user)
    mydb.add_house(house_name, key)
    houses = mydb.get_user_houses((key,))

    if not auto:
        user.busy = False

    if houses is not None and len(houses) != 0:
        house_id = houses[0][0]
        id_int = \
            mydb.add_item(house_id, 0, house_name, "dom", user.id, "house", "house", demo_role=demo_role,
                          has_img=has_img)[
                0]

        # Reloading all user's houses if adding a new house
        get_items(user, dom)
        current_dir = get_dir(id_int, dom, user)
        if not auto:
            dir_txt = show_dir(current_dir, dom, user, False)
            user.step = Step("main_menu", id_int)
            send_item_to_user(user, dir_txt, "house")
        return current_dir


def get_and_add_unique_key(user):
    key = rt.get_random_string(32)
    db_reply = mydb.check_is_ok(key)
    if db_reply[1]:
        mydb.add_access_key(user, key)
        return key


def step_lang_choice_first(user, msg):
    step_lang_choice(user, msg, True)


def step_lang_choice(user, msg, first_start=False):
    if not first_start:
        if if_canceled(user, msg):
            return

    if not first_start:
        send_msg_txt(user.id, "⏳")

    user.lang = "en"
    if msg.text in {'Русский', 'русский', 'Russian', 'russian', 'Ru', 'RU', 'ru'}:
        user.lang = "ru"
    reply = t("lang_chosen", user)
    if first_start:
        user.step = Step("main_menu", 0)
    mydb.save_user(user)
    if not first_start:
        send_msg_txt(user.id, reply)

    if not first_start:
        if user.name is None:
            go_to_change_name(user, msg)
            return
        go_to_main_menu(user, msg)
    else:
        go_to_about(user, msg, startup=True)
        time.sleep(3)
        go_to_offer_demo(user, msg)


def filter_text(txt, max_len=128):
    txt = re.sub(r'[^a-zA-Zа-яА-Я0-9-.,:;\'’() ёЁ]', '', txt)
    if len(txt) > max_len:
        txt = txt[:max_len]
    return txt


def step_change_name(user, msg):
    if if_canceled(user, msg):
        return

    name = filter_text(msg.text)
    reply = f"{t('name_changed_to', user)} {name}"
    user.name = name
    mydb.save_user(user)
    send_msg_txt(user.id, reply)
    go_to_main_menu(user, msg)


def set_user_status(user, txt, status, status_value=True):
    try:
        user_id = int(txt.split()[1])
        success = mydb.update_user_status(user_id, status, status_value)

        if not success:
            send_msg_txt(user.id, f"User {user_id} not found or wasn't changed")
            return

        loaded_user = next((x for x in users if x.id == user_id), None)
        if loaded_user is not None:
            if status == 'admin':
                loaded_user.admin = status_value
            if status == 'premium':
                loaded_user.premium = status_value
                if status_value:
                    send_msg_txt(user_id, t('premium_version_activated', loaded_user))
                send_msg_txt(user.id, f'Status {status} = {status_value} set for {loaded_user.name}')

        return True
    except Exception as exp:
        print(f"Can't set user status {status}: {txt}, exception: {exp}")
        return False


def special_words_check(telegram_id, msg):

    # Working with stickers
    if msg.text is None:
        if msg.sticker is not None:
            if 'wrw' in special_topics_dic.keys():
                if msg.sticker.set_name.lower() in special_topics_dic['wrw']:
                    send_msg_txt(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
                    save_request_to_file(telegram_id, 'sticker', os.path.join('conversation_logs', 'special_topics.log'))
                    return True
        return False

    # Working with text
    found = False

    if 'wrw' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['wrw']):
            send_msg_txt(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
            save_request_to_file(telegram_id, 'flag', os.path.join('conversation_logs', 'special_topics.log'))
            found = True

    if 'belarus' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['belarus']):
            send_msg_txt(telegram_id, "Жыве вечна!", remove_keyboard=False)
            time.sleep(1)
            send_msg_txt(telegram_id, random.choice(random_belarus_stickers), False, True, remove_keyboard=False)
            save_request_to_file(telegram_id, msg.text, os.path.join('conversation_logs', 'special_topics.log'))
            found = True

    if 'ukraine' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['ukraine']):
            send_msg_txt(telegram_id, "Героям слава!", remove_keyboard=False)
            time.sleep(1)
            save_request_to_file(telegram_id, msg.text, os.path.join('conversation_logs', 'special_topics.log'))
            found = True

    if 'censored' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['censored']):
            send_msg_txt(telegram_id, "🙈", remove_keyboard=False)
            save_request_to_file(telegram_id, msg.text, os.path.join('conversation_logs', 'censored.log'))
            found = True

    if 'humiliation' in special_topics_dic.keys():
        if any(l in msg.text.lower() for l in special_topics_dic['humiliation']):
            send_msg_txt(telegram_id, 'CAACAgIAAxkBAAIWHl_hIO765r2tvb0KFSjENVvhJc5VAAJZAAOELrgGmubs-nA_1bseBA', False,
                         True,
                         remove_keyboard=False)
            save_request_to_file(telegram_id, msg.text, os.path.join('conversation_logs', 'humiliation.log'))
            found = True

    return found


def check_service_cmds(telegram_id, msg, user):
    if user is None or not isinstance(user, User) or not user.admin or msg.text is None:
        return False

    cmd_activated = False
    status_value = True
    success = False

    if msg.text.lower().startswith('no'):
        status_value = False

    if msg.text.lower().startswith(('premium ', 'no_premium')):
        success = set_user_status(user, msg.text, 'premium', status_value)
        cmd_activated = True

    if telegram_id in devs and msg.text.lower().startswith(('admin ', 'no_admin')):
        success = set_user_status(user, msg.text, 'admin', status_value)
        cmd_activated = True

    if not cmd_activated:
        return False

    if success:
        send_msg_txt(telegram_id, "Done!")
        return True
    else:
        send_msg_txt(telegram_id, "Error occurred while setting user status!")
        return True


def work_on_msg(telegram_id, msg, users):
    if special_words_check(telegram_id, msg):
        return

    if msg.text is not None and msg.text == "/start":
        send_msg_txt(telegram_id, """*Welcome to DomData!* \n         ...please wait...""")

    user = find_or_create_user(msg, users)

    if check_service_cmds(telegram_id, msg, user):
        return

    if user == 'startup':
        return

    if user is not None and user.step.name == 'lang_choice_first':
        step_lang_choice_first(user, msg)
        return

    if user is not None and user.step.name == 'offer_demo':
        continue_startup(user, msg)
        return

    if user is None:
        send_msg_txt(telegram_id, "User was not found and could not be created")
        return

    user.update_use_date()

    if not user.activated:
        return

    # limit check
    ok = user.new_action(content=msg)

    if not ok or user.busy:
        send_msg_txt(msg.chat.id, "⏳", remove_keyboard=False)
        return

    if msg.text in ['/faq', '/help', 'Help', 'Помощь']:
        go_to_help(user, msg)
        return

    if msg.content_type == "sticker":
        time.sleep(1)
        send_msg_txt(telegram_id, random.choice(random_stickers), False, True, remove_keyboard=False)
        return

    if msg.content_type == "photo":
        if user.step.name in ("new_item_type", "main_menu"):
            if user.step.name == "main_menu":
                u_location = user.step.location
                u_parent = find_item_by_id(u_location, dom, user)

                # Quickly adding an item with a picture (without selecting the New Item command),
                # not available at the house and floor levels
                if u_parent.type in ("house", "dom", "level"):
                    send_msg_txt(telegram_id, t("img_unexpected", user), remove_keyboard=False)
                    return
            if user.step.new_item_type == "":
                user.step.new_item_type = "item"
            step_new_item(user, msg)
        elif user.step.name == "new_item":
            step_new_item(user, msg)
        elif user.step.name == "search_by_name":
            step_search_by_name(user, msg)
        elif user.step.name == "add_img":
            step_add_img(user, msg)
        else:
            send_msg_txt(telegram_id, t("img_unexpected", user), remove_keyboard=False)
            # previous_step(user, msg)
        return

        # Comparing only the first 64 characters, because the text in the button has length limit
    if user.item_in_hands_put_but_text is not None and msg.text[:64] == user.item_in_hands_put_but_text[:64]:
        put_it_here(user, msg)
        return

    func = user_commands.get(msg.text)
    if func is not None:
        func(user, msg)
        return

    func = steps_func_dic.get(user.step.name)
    if func is None:
        return

    func(user, msg)


def create_new_user(msg, users, id_instead_of_msg=False):
    if id_instead_of_msg:
        uid = msg
        name = "Unknown"
        lang = "en"
    else:
        uid = msg.chat.id
        name = msg.from_user.first_name
        lang = msg.from_user.language_code

    if not id_instead_of_msg:
        send_msg_txt(msg.chat.id, "⏳")

    loaded_user_tuple = mydb.get_user(uid)

    # standard values
    premium = False
    admin = False

    if loaded_user_tuple is not None:
        if loaded_user_tuple[1] is not None:
            name = loaded_user_tuple[1]
        if loaded_user_tuple[2] is not None:
            lang = loaded_user_tuple[2]
        premium = loaded_user_tuple[3]
        admin = loaded_user_tuple[4]

    is_activated = True
    if loaded_user_tuple is None:
        is_activated = False

    if lang is not None and lang not in allowed_languages:
        lang = "en"
    new_user = User(uid, name, "start", lang, activated=is_activated, premium=premium, admin=admin)

    users.add(new_user)
    brand_new = False
    if loaded_user_tuple is None:
        brand_new = True
        mydb.save_user(new_user)
        send_msg_to_developer(f'New user:\nUser: {new_user.name} {new_user.id}')

    return [new_user, brand_new]


def find_or_create_user(msg, users, id_instead_of_msg=False):
    user_non_flag = False
    first_start = False

    with user_loading_lock:
        if id_instead_of_msg:
            user = next((u for u in users if u.id == msg), None)
        else:
            user = next((u for u in users if u.id == msg.chat.id), None)
        if user is None:
            user_non_flag = True
            res = create_new_user(msg, users, id_instead_of_msg)
            user = res[0]
            if res[1]:
                first_start = True

        if user.busy:
            return user

    if user_non_flag:
        if first_start:

            if user.lang != 'ru':
                go_to_change_lang(user, msg, first_start=True)
            else:
                go_to_about(user, msg, startup=True)
                time.sleep(3)
                go_to_offer_demo(user, msg)
            # A flag that indicates there is no need to go further,
            # but wait for a response from the user about the language
            return 'startup'
        else:
            get_items(user, dom)

    return user


def continue_startup(user, msg):
    if user.busy:
        return

    create_demo_house(user, msg, True)
    user.activated = True
    time.sleep(7)
    send_msg_txt(user.id, t('dd_video_tutorial', user), remove_keyboard=False, must_close_tags=False)


def search_item_by_class_or_emoji(query, my_things, by_emoji=False, top_level_only=False):
    found_results_list = []

    for thing in my_things:
        if by_emoji:
            value = thing.item_emoji
        else:
            value = thing.item_class

        if value == query:
            found_results_list.append({'item': thing, 'min_dist': 0})

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_class_or_emoji(query, thing.space, by_emoji)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list


def normalize_tags(tags):
    min = tags[-1]['c']
    max = tags[0]['c']
    range = max - min
    for t in tags:
        t['c'] = (t['c'] - min) * (max / range)

    return tags


def find_tags_distance(tags1_i, tags2_i):
    if tags1_i is None or tags2_i is None:
        return None

    tags1 = copy.deepcopy(tags1_i)
    tags2 = copy.deepcopy(tags2_i)

    if len(tags1) > len(tags2):
        tags1 = tags1[:len(tags2)]
    if len(tags2) > len(tags1):
        tags2 = tags2[:len(tags1)]

    dist = 0
    all_tags = set()

    for t1 in tags1:
        all_tags.add(t1.get("tag"))

    for t2 in tags2:
        all_tags.add(t2.get("tag"))

    for k in all_tags:
        a1 = next((x for x in tags1 if x["tag"] == k), None)
        a2 = next((x for x in tags2 if x["tag"] == k), None)
        if a1 is None:
            dist += a2["c"]
        elif a2 is None:
            dist += a1["c"]
        elif a1 is not None and a2 is not None:
            dist += abs(a1["c"] - a2["c"])
        else:
            print("No way:)")

    return dist


def search_item_by_photo(stags, my_things, max_dist=100, top_level_only=False):
    found_results_list = []

    for thing in my_things:

        if thing.tags is not None and len(thing.tags) != 0 and thing.type not in {"house", "dom", "level", "room"}:
            dist = find_tags_distance(stags, thing.tags)
            if dist is not None and dist < max_dist:
                found_results_list.append({'item': thing, 'min_dist': dist})

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_photo(stags, thing.space, max_dist)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list


def replace_multiply_strings_to_one(s, new_c=None, c_array=None):
    if c_array is None:
        c_array = [",", ".", ";", ":", "(", ")", "-", "+", "[", "]", "}", "{"]
    if new_c is None:
        new_c = ""
    for c in c_array:
        s = s.replace(c, new_c)
    return s


def search_item_by_part_of_name(query, my_things, distance_limit, top_level_only=False, things_only=False):
    query = query.lower()
    query = replace_multiply_strings_to_one(query)
    query = query.replace('ё', "е")

    found_results_list = []

    for thing in my_things:

        s_inf = {'close_words_factor': 0}
        min_dist = 100

        for qw in query.split():
            th_name = thing.name
            th_name = th_name.lower()
            th_name = replace_multiply_strings_to_one(th_name)
            th_name = th_name.replace('ё', "е")
            for word in th_name.split():
                if len(qw) > len(word):
                    long_word_len = len(qw)
                else:
                    long_word_len = len(word)
                dist = compare(word, qw)
                if dist < distance_limit and (dist / long_word_len * 5) < min_dist:
                    min_dist = dist / long_word_len * 5
                if dist == 0:
                    v = 4 - len(word)
                    if v < min_dist:
                        s_inf['close_words_factor'] = s_inf['close_words_factor'] + v
                        min_dist = v

        if min_dist <= distance_limit:
            if not (thing.item_class in {'dom', 'house', 'level', 'room', 'cupboard', 'storage',
                                         'box'} and things_only):
                s_inf.update({'item': thing, 'min_dist': min_dist})
                found_results_list.append(s_inf)

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_part_of_name(query, thing.space, distance_limit)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list


def sort_results_by_words_and_full_distance(all_results, query, max_total_dist=50):
    for one_r in all_results:
        all_name_dist = compare(one_r['item'].name, query)
        if one_r['min_dist'] <= 0:
            all_name_dist = all_name_dist / 6
        if 0 < one_r['min_dist'] <= 1:
            all_name_dist = all_name_dist / 3
        if len(one_r['item'].name.split()) == 1 and one_r['min_dist'] > 1:
            all_name_dist = all_name_dist * 4
        one_r.update({'all_name_dist': all_name_dist})
        one_r.update({'total_dist': one_r['min_dist'] + one_r['all_name_dist'] / 2 + one_r['close_words_factor'] * 2})

    max_dist_from_length = len(query) / 3
    if max_dist_from_length < 2:
        max_dist_from_length = 2

    all_results = list(
        filter(lambda r: r['total_dist'] < max_total_dist or r['min_dist'] < max_dist_from_length, all_results))

    return sorted(all_results, key=lambda r: r['total_dist'], reverse=False)


def find_item_by_id(input_id, my_things, user, convert=False):
    for thing in my_things:
        if convert:
            id = user.id_conv(input_id, False)
        else:
            id = input_id
        if id == thing.id:
            return thing
        if len(thing.space) != 0:
            item = find_item_by_id(input_id, thing.space, user, convert)
            if item is not None:
                return item
    return None


def find_item_path(user, item, items, include_self_name=False, include_emoji=False, include_class=True,
                   first_turn=False):
    item_class_str = ""
    item_self_name_str = ""
    item_emoji_str = ""

    if include_self_name:
        if item.item_class is not None and item.item_class is not None and include_class:
            item_class_str = f" ({t(item.item_class, user).lower()})"

        if include_emoji:
            if item.item_emoji is not None:
                item_emoji_str = item.item_emoji + " "

        item_self_name_str = f"\n{item_emoji_str}*{item.name}*{item_class_str}"

    if item.location not in {-1, 0}:
        parent = find_item_by_id(item.location, items, user)
        user.update_dic(parent.id)
        up_path = find_item_path(user, parent, items, False, include_emoji, include_class)

        if parent is None:
            return "/DomData"

        parent_class_str = ""
        if parent.item_class is not None and include_class:
            parent_class_str = f" ({t(parent.item_class, user).lower()})"

        parent_emoji_str = ""
        if include_emoji:
            if parent.item_emoji is not None:
                parent_emoji_str = parent.item_emoji + " "

        first_turn_str = ""
        if first_turn:
            first_turn_str = "\n      /up ⬆️"

        full_path = f"{up_path}\n/{user.id_conv(parent.id)} {parent_emoji_str}_{parent.name}{parent_class_str}_{first_turn_str}{item_self_name_str}"

        if full_path.count('\n') > 1 and t('path', user) not in full_path:
            p = full_path.find('\n') + 1
            full_path = full_path[:p] + f"{t('path', user)}:\n" + full_path[p:]

        return full_path
    else:

        first_turn_str = ""
        if first_turn and item.location == 0:
            first_turn_str = "\n      /up ⬆️"

        return f"/DomData{first_turn_str}{item_self_name_str}"


def format_path(path):
    if path == '/DomData':
        return path

    content = path.split(':\n')

    lines = content[len(content) - 1].split('\n')
    nlines = len(lines)
    max_tabs = 5

    levels = nlines - 1

    tab_c = 1
    this_iter = 0

    new_path = ''

    for l in lines:
        this_tab = ' ' * tab_c

        l = this_tab + l

        max_length = 48
        if len(l) > max_length:
            l = f"{l[:max_length - 3]}..._"

        this_iter += 1

        if this_iter >= 1 and tab_c < max_tabs:
            this_iter = this_iter - 1
            tab_c += 1

        new_path += l + '\n'

    if len(content) > 1:
        new_path = content[0] + ':\n' + new_path
    return new_path[0:-2]


# returns a string displaying the object, the path to it, its contents, etc.,
def show_dir(item, items, user, top):
    dir_txt = ""
    hands_txt = ""

    full_path = find_item_path(user, item, items, first_turn=True)

    full_path = format_path(full_path)

    if user.item_in_hands is not None:
        item_emoji_txt = ""
        item_class_txt = ""
        if user.item_in_hands.item_emoji is not None:
            item_emoji_txt = user.item_in_hands.item_emoji + " "
        if user.item_in_hands.item_class is not None:
            item_class_txt = f" ({t(user.item_in_hands.item_class, user).lower()})"
        hands_txt = f"\n🤲 {item_emoji_txt}*{user.item_in_hands.name}*{item_class_txt} {t('in_my_hands', user)}\n\n"

    location = item.location
    parent = find_item_by_id(location, items, user)
    location_str = str(location)
    if parent is not None:
        location_str = location_str + f" {parent.name}"
    if location == 0:
        location_str = f"{t('my_doms_command', user)}"
    if top:
        dir_txt = f"{item.name}:"
    else:
        item_emoji = ""
        two_dots = f":\n                _{t('empty', user)}_"
        if len(item.space) > 0:
            two_dots = ":"
        if item.item_emoji is not None:
            item_emoji = item.item_emoji + " "
            if len(item.space) == 0:
                item_emoji = "      " + item.item_emoji
        item_id_line_only_if_not_empty = f"/{user.id_conv(item.id)} "
        item_class_str = ""
        if item.item_class is not None and item.item_class != '':
            item_class_str = f" ({t(item.item_class, user).lower()})"
        taken_by_line = ""
        if item.taken_by_user is not None:
            uname = get_user_name(item.taken_by_user)
            date_line = ""
            if item.last_taken_date is not None:
                date_line = f" ({item.last_taken_date.strftime(t('date_format', user))})"
            taken_by_line = f"❗️_{t('taken_by_user', user)} - {uname}_\n{date_line}"

        highlighted_by_line = ""
        if item.highlighted_by is not None:
            uname = get_user_name(item.highlighted_by)
            date_line = ""
            if item.highlighted_date is not None:
                date_line = f" ({item.highlighted_date.strftime(t('date_format', user))})"
            highlighted_by_line = f"☝️_{t('highlighted_by_user', user)} - {uname}{date_line}_\n"

        dir_txt = dir_txt + f"{hands_txt}{full_path}\n\n_{t('youre_in', user)}_ ⬇\n➡ {item_emoji}{item_id_line_only_if_not_empty}*{item.name}*{item_class_str}{two_dots}\n{taken_by_line}{highlighted_by_line}"
    if item is not None:

        item.space = sorted(item.space, key=lambda r: r.date, reverse=False)

        for it in item.space:
            user.update_dic(it.id)
            inside_str = ""
            item_emoji = "      "

            has_img = ""
            if it.has_img and it.item_class not in {'house', 'dom', 'level', 'room', 'cupboard', 'storage', 'box'}:
                has_img = " 📷"

            it_class_str = ""
            if it.item_class is not None and it.item_class != '' and it.item_emoji is None and len(it.space) == 0:
                it_class_str = f" ({t(it.item_class, user).lower()})"

            if it.item_emoji is not None:
                item_emoji = it.item_emoji + " "
            if len(it.space) > 0:
                items_count_and_emoji_inside = count_items_inside(it, True)
                emoji_top = ""
                if items_count_and_emoji_inside[0] != 0:
                    if len(items_count_and_emoji_inside[1]) != 0 and it.type not in {'dom', 'house', 'level'}:
                        emoji_top = f"{emoji_chart(items_count_and_emoji_inside[1], 8)}"
                        inside_str = f" ({items_count_and_emoji_inside[0]} {emoji_top})"
                    else:
                        inside_str = f" ({items_count_and_emoji_inside[0]} _{t('items_inside', user)}_)"

            # If the item was taken away, don't show the id of the items inside,
            # to prevent entering them
            show_or_hide_id = f"/{user.id_conv(it.id)}"
            if item.taken_by_user is not None:
                show_or_hide_id = ""

            # If the item was taken away, mark it with an exclamation point
            it_taken = ""
            if it.taken_by_user is not None:
                it_taken = "❗️"

            it_highlighted = ""
            if it.highlighted_by is not None:
                it_highlighted = "☝️"

            dir_txt += f"\n         {item_emoji}{show_or_hide_id} – {it_taken}{it_highlighted}{it.name}{it_class_str}{it_highlighted}{it_taken}{has_img}{inside_str}"

        comments_line = ""
        if item.comment is not None:
            if item.commented_by_user is not None:
                uname = get_user_name(item.commented_by_user)
            else:
                uname = ""
            comments_line = f"\n\n✍️️*{t('commented_by_user', user)}:*\n{item.comment}\n_{uname} ({item.comment_date.strftime(t('date_format', user))}_)"

        missing_things_line = ""
        if location == 0 and len(item.dom_missing_things) != 0:
            missing_things_line = f"\n\n❗️*{t('missing_things', user)}:*"
            for mis in item.dom_missing_things:
                ie = "       "
                if mis.item_emoji is not None:
                    ie = mis.item_emoji + " "
                missing_things_line += f"\n/{user.id_conv(mis.id)} {ie}_{mis.name}_"

        highlighted_things_line = ""
        if location == 0 and len(item.dom_highlighted_things) != 0:
            highlighted_things_line = f"\n\n☝️*{t('highlighted_things', user)}:*"
            for hi in item.dom_highlighted_things:
                ic = ""
                if hi.comment is not None:
                    com = hi.comment
                    if len(com) > 32:
                        com = f"{com[:32]}..."
                    ic = f" (_{com}_)"
                ie = "       "
                if hi.item_emoji is not None:
                    ie = hi.item_emoji + " "
                highlighted_things_line += f"\n/{user.id_conv(hi.id)} {ie}{hi.name}{ic}"

        dir_txt += comments_line + missing_things_line + highlighted_things_line

        if user.last_put_item_location is not None and user.item_in_hands is not None:
            b_e = ""
            if user.last_put_item_location.item_emoji is not None:
                b_e = user.last_put_item_location.item_emoji + " "

            if user.last_put_item_location.id != item.id:
                dir_txt += f"\n\n{t('go_back_to', user)}  {b_e}/{user.id_conv(user.last_put_item_location.id)} {user.last_put_item_location.name}"
            user.last_put_item_location = None

        if user.last_take_item_location is not None and user.item_in_hands is None:
            b_e = ""
            if user.last_take_item_location.item_emoji is not None:
                b_e = user.last_take_item_location.item_emoji + " "

            if user.last_take_item_location.id != item.id:
                dir_txt += f"\n\n{t('go_back_to', user)} {b_e}/{user.id_conv(user.last_take_item_location.id)} {user.last_take_item_location.name} "
            user.last_take_item_location = None

        return dir_txt
    else:
        return "Not found"


def emoji_chart(emojies, top=10):
    counter = collections.Counter(emojies)
    res = counter.most_common(top)
    fin_res = ""
    for r in res:
        fin_res = fin_res + r[0]
    return fin_res


def get_dir(id, items, user, by_user=False):
    item = find_item_by_id(id, items, user, by_user)

    if id == 0:
        top = True
        filtered_items = list(items)
        filtered_items = list(filter(lambda item: item.dom_id in user.houses, filtered_items))
        for fi in filtered_items:
            user.update_dic(fi.id)
        item = Item(0, f"{t('my_doms', user)}", -1, "top", datetime.datetime.now(), 0, None, None, 0, None, None, None,
                    filtered_items)
        return item

    top = False
    if item is None:
        return None
        # return None instead of the top level if not found, so that we first display a message "Not found"
        # And only then - go to the top level (when we don't find the object)

    else:
        if item.dom_id not in user.houses:
            return None

    return item


def count_items_inside(item, first=False):
    emojies = []
    count = 1

    # Not considering houses, floors, rooms as items to count
    if item.item_class in ['house', 'dom', 'level', 'room'] or first:
        count = 0

    if len(item.space) == 0:
        if item.item_emoji is not None and item.item_emoji != "" and item.item_class not in {'house', 'dom', 'level',
                                                                                             'room', 'cupboard',
                                                                                             'storage', 'box'}:
            emojies.append(item.item_emoji)
        return [count, emojies]
    else:
        for it in item.space:
            res = count_items_inside(it)
            count = count + res[0]
            emojies.extend(res[1])

        if count < 0:
            pass

        return [count, emojies]


def remove_missing_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_missing_things = [it for it in item_dom.dom_missing_things if it.id != item.id]


def add_missing_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_missing_things = [it for it in item_dom.dom_missing_things if it.id != item.id]
    item_dom.dom_missing_things.append(item)


def remove_highlighted_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_highlighted_things = [it for it in item_dom.dom_highlighted_things if it.id != item.id]


def add_highlighted_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_highlighted_things = [it for it in item_dom.dom_highlighted_things if it.id != item.id]
    item_dom.dom_highlighted_things.append(item)


def find_item_dom(item, user, items):
    if item.location == 0:
        return item
    else:
        parent = find_item_by_id(item.location, items, user)
        return find_item_dom(parent, user, items)


def go_to_parent(child, my_things):
    for thing in my_things:
        if thing.id == child.id:
            continue
        if child.location == thing.id:
            thing.space.append(child)
            return True
        if len(thing.space) != 0:
            success = go_to_parent(child, thing.space)
            if success:
                return True


def delete_someone_elses(user, items):
    houses = []
    for h in user.houses:
        houses.append(h[0])

    for i, o in enumerate(items):
        if o.dom_id not in houses:
            del items[i]


def delete_mine(user, base):
    temp_dom = list(dom)

    for d in temp_dom:
        if d.dom_id in user.houses:
            base.remove_by_dom(d.dom_id)
            dom.remove(d)


def formItemFromDB(it):
    return Item(it[0], it[1], it[2], it[3], it[4], it[5], it[6], it[7], it[8], it[9], it[10], it[11], None, it[12],
                it[13], it[14], it[15], it[16], it[17], it[18], it[19], it[20], it[21], it[22], it[23], it[24], it[25],
                it[26])


def formIbase(ib):
    things_from_base = mydb.get_items_for_ibase([all_item_fields, "dom"])

    for it in things_from_base:
        item = formItemFromDB(it)
        ib.append(item)
        if item.type in {'dom', 'house'}:
            dom.append(item)


def get_items(user, items):
    if user.loading:
        return

    user.loading = True

    user.houses = []
    temp_houses = get_user_houses(user)

    # if the user doesn't have rights to any house, then leave
    if len(temp_houses) == 0:
        user.loading = False
        return

    for h in temp_houses:
        user.houses.append(h[0])

    things_from_base = mydb.get_everything([all_item_fields, "dom"], user.houses)

    delete_mine(user, ibase)

    for it in things_from_base:
        item = formItemFromDB(it)

        already_exists = ibase[item.id]

        user.update_dic(item.id)

        if already_exists is None:
            items.append(item)
            # adding not only to the dom list with a hierarchy,
            # but also to the list without a hierarchy for searching
            ibase.append(item)
        else:
            pass
            # duplicate detected?

    sort_dom(items, user)

    user.loading = False


def sort_dom(items, user):
    while len(list(filter(lambda item: item.location != 0, items))) > 0:
        for thing in items:
            if thing.taken_by_user is not None:
                add_missing_thing(thing, user, items)
            if thing.highlighted_by is not None:
                add_highlighted_thing(thing, user, items)
            if thing.location == 0:
                continue
            found = go_to_parent(thing, items)
            if found:
                try:
                    items.remove(thing)
                except Exception as ex:
                    logger.error("error while sorting dom:", ex)


logger.info("DomData server started")


def send_msg_txt_and_video(m, txt, vid, file_id=None, keyboard=None):
    logger.debug(f"Sending a message {txt} with video to user {m}")
    done = False
    tries = 0

    txt = close_tags(txt)

    if file_id is not None:
        attachment = file_id
    else:
        attachment = vid

    while not done and tries < 10:
        try:

            if keyboard is None:
                inf = bot.send_video(m, data=attachment, caption=txt,
                                     parse_mode='Markdown', supports_streaming=True)
            else:
                inf = bot.send_video(m, data=attachment, caption=txt, reply_markup=keyboard,
                                     parse_mode='Markdown', supports_streaming=True)

            done = True
        except Exception as error:
            attachment = vid
            tries = tries + 1
            logger.exception("Can't send message to Telegram, Error: ")


def send_msg_txt_and_keyboard(m, txt, keyboard, pic=None, item=None, must_close_tags=True):
    logger.debug(f"Sending a message {txt} with keyboard {keyboard} to user {m}, image - {pic}")
    done = False
    tries = 0

    add_txt = None

    if pic is not None and len(txt) > 1024:
        txt_lines = txt.splitlines()
        add_txt_lines = []
        while len(txt) > 1024:
            add_txt_lines.append(txt_lines.pop(-1))
            txt = '\n'.join(txt_lines)

        add_txt_lines.reverse()
        add_txt = '\n'.join(add_txt_lines)

    if must_close_tags:
        txt = close_tags(txt)

    while not done and tries < 10:
        try:
            if pic is None or pic is False:
                bot.send_message(
                    m, txt,
                    reply_markup=keyboard, parse_mode="Markdown")
            else:

                if item is not None and item.file_id is not None and tries < 2:
                    inf = bot.send_photo(m, photo=item.file_id, caption=txt, reply_markup=keyboard,
                                         parse_mode='Markdown')
                else:

                    send_msg_txt(m, "⏳")

                    path = myfiles.download_pic(pic)
                    if path is None:
                        it_id = pic
                        if item is not None:
                            it_id = item.id
                        mydb.update_item("dom", "id", "has_img", False, it_id)

                        user = find_or_create_user(m, users, True)
                        it = find_item_by_id(it_id, dom, user)
                        it.has_img = False
                        send_msg_txt(m, "error: file not found")
                        return

                    inf = bot.send_photo(m, open(path, 'rb'), txt, reply_markup=keyboard, parse_mode='Markdown')

                    if inf is not None:
                        file_id = inf.photo[0].file_id
                        item.file_id = file_id
                        update_item_attribute(None, None, "file_id", file_id, True, item)
                    else:
                        logger.error("picture error")
                    myfiles.delete_file(path)

            done = True
        except Exception as error:
            tries = tries + 1
            logger.exception(f"Can't send message to Telegram, Error: {error}")

    if add_txt is not None:
        send_msg_txt(m, add_txt, remove_keyboard=False)


def close_tags(txt):
    tags = ['*', '_', '`']

    for tag in tags:
        if txt.count(tag) % 2 != 0:
            last_char_index = txt.rfind(tag)
            txt = txt[:last_char_index] + "" + txt[last_char_index + 1:]

    txt.replace('[', '')
    txt.replace(']', '')

    return txt


def send_msg_txt(uid_or_msg, txt, reply=False, sticker=False, remove_keyboard=True, must_close_tags=True):
    logger.debug(f"Sending a message {txt} to user {uid_or_msg}")

    if txt == '':
        return

    text_parts = []
    # 4096
    limit_chars = 4096

    while len(txt) > limit_chars:
        crop_line = txt.rfind("\n", 0, 3600)

        text_parts.append(txt[:crop_line])
        txt = txt[crop_line:]
    text_parts.append(txt)

    for tp in text_parts:

        if must_close_tags:
            tp = close_tags(tp)

        done = False
        tries = 0
        while not done and tries < 10:
            try:
                if reply and type(uid_or_msg) is not int:
                    bot.reply_to(uid_or_msg, tp, parse_mode='Markdown')
                elif sticker:
                    bot.send_sticker(uid_or_msg, tp)
                else:
                    if remove_keyboard:
                        bot.send_message(uid_or_msg, tp, reply_markup=types.ReplyKeyboardRemove(),
                                         parse_mode='Markdown')
                    else:
                        bot.send_message(uid_or_msg, tp, parse_mode='Markdown')
                done = True
            except Exception as error:
                tries = tries + 1
                logger.exception(f"Can't send message to Telegram, Error: {error}")
                time.sleep(1 + tries)
                # start_polling(bot)


def keyboard(args):
    resize_keyboard = False
    if len(args) < 2:
        resize_keyboard = True

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=resize_keyboard)
    for arg in args:
        btn = types.KeyboardButton(arg)
        markup.add(btn)
    return markup


def send_msg_to_developer(txt):
    for dev in devs:
        send_msg_txt(dev, txt, remove_keyboard=False)


send_msg_to_developer('DomData server started')


@bot.message_handler(commands=['starttest'])
def send_welcome_txt(message):
    bot.send_message(
        message.chat.id,
        '''Добро пожаловать. ✌
        ''',
        reply_markup=keyboard("Кнопка"))


@bot.message_handler(content_types=['document'])
def send_msg(message):
    send_msg_txt(message.chat.id,
                 "❌\nUnsupported format - Данный формат не поддерживается\n\nPlease, send pictures as photos, not as files\nПожалуйста, отправляйте изображения как фото, а не как файлы",
                 remove_keyboard=False)


@bot.message_handler(content_types=['audio'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['video'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['location'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['contact'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['videonote'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['voice'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['video_note'])
def send_msg(message):
    send_msg_txt(message.chat.id, "🤷‍♀️🤷‍♂️", remove_keyboard=False)


@bot.message_handler(content_types=['sticker'])
def send_sticker(message):
    work_on_msg(message.chat.id, message, users)


@bot.message_handler(content_types=['text'])
def send_welcome_txt(message):
    work_on_msg(message.chat.id, message, users)


@bot.message_handler(content_types=['photo'])
def send_msg(message):
    work_on_msg(message.chat.id, message, users)
    return


steps_func_dic = {
    'start': step_start,
    'lang_choice': step_lang_choice,
    'lang_choice_first': step_lang_choice_first,
    'change_name': step_change_name,
    'main_menu': step_main_menu,
    'new_house': step_new_house,
    'new_level': step_new_level,
    'new_room': step_new_room,
    'new_item': step_new_item,
    'new_item_type': step_new_item_type,
    'new_item_class': step_new_item_class,
    'new_item_emoji': step_new_item_emoji,
    'similar_object': step_similar_object,
    'rename_item': step_rename_item,
    'comment_item': step_comment_item,
    'delete_item': step_delete_item,
    'add_img': step_add_img,
    'delete_img': step_delete_img,
    'search': step_search,
    'search_by_name': step_search_by_name,
    'search_by_class': step_search_by_class,
    'search_by_emoji': step_search_by_emoji,
    'share_access': step_share_access,
    'share_access_add': step_share_access_add,
    'new_item_class_update': step_new_item_class_update,
    'new_item_emoji_update': step_new_item_emoji_update
}

user_commands = dict.fromkeys(['👤 Change my name', '👤 Поменять мое имя'], go_to_change_name)
user_commands.update(dict.fromkeys(
    ['/up', '/Up', '⬆️Go up', '⬆️Наверх', '⬆️Go up (show all my houses)', '⬆️Наверх (к списку моих домов)',
     '⬆️Go up (show all floors)', '⬆️Наверх (к списку этажей)'], go_up))
user_commands.update(
    dict.fromkeys(['/demohouse', '🏗 New demo house', '🏗 Новый демонстрационный дом'], create_demo_house))
user_commands.update(dict.fromkeys(
    ['🌐 Change my language', '🌐 Поменять мой язык', '🌐 Поменять язык', '/LanguageSettings', '/languageSettings',
     '/language'], go_to_change_lang))
user_commands.update(dict.fromkeys(['/faq', '/help', '/Help', '/f1', '🆘 Help', '/FAQ', '🆘 Помощь', 'Back to FAQ',
                                    'Назад к списку часто задаваемых вопросов'], go_to_help))
user_commands.update(dict.fromkeys(['ℹ️About', 'ℹ️ About', 'ℹ️О проекте', 'ℹ️ О проекте', '/about'], go_to_about))
user_commands.update(dict.fromkeys(['/goback', 'Where am I?', 'Где я?', '/refresh'], previous_step))

user_commands.update(dict.fromkeys(['/help_tutorial', '📺 VIDEO TUTORIAL 📺', '📺 ОБУЧАЮЩЕЕ ВИДЕО 📺'], help_tutorial))
user_commands.update(dict.fromkeys(['/help_about', 'How does it work?', 'Как это работает?'], help_about))
user_commands.update(dict.fromkeys(['/help_basics', 'How to use it?', 'Как пользоваться?'], help_basics))
user_commands.update(
    dict.fromkeys(['/help_navigation', 'How do I navigate?', 'Как мне перемещаться по виртуальному дому?'],
                  help_navigation))
user_commands.update(
    dict.fromkeys(['/help_premium', '⭐️Do I need Pro Version?', '⭐️Что дает полная версия DomData?'], help_premium))
user_commands.update(
    dict.fromkeys(['/help_keyboard', '/nokeyboard', 'Where is the keyboard?', 'Куда пропала клавиатура?'],
                  help_keyboard))
user_commands.update(dict.fromkeys(['/help_location', 'What if my things were rearranged in the real life?',
                                    'Что делать, если в реальности вещь переложили?'], help_location))
user_commands.update(dict.fromkeys(
    ['/help_conception', 'So every time when I put a plate on the table should I do the same in DomData?',
     'То есть каждый раз, когда я ставлю тарелку на стол, мне нужно сделать это и в DomData?'], help_conception))
user_commands.update(
    dict.fromkeys(['/help_search', 'How do I search in DomData?', 'Как найти нужную мне вещь?'], help_search))
user_commands.update(
    dict.fromkeys(['/help_access', 'Is there family sharing in DomData?', 'Как пользоваться DomData всей семьей?'],
                  help_access))
user_commands.update(
    dict.fromkeys(['/help_security', 'Is it safe? Can my house be hacked?', 'Могут ли взломать мой дом?'],
                  help_security))
user_commands.update(dict.fromkeys(
    ['/help_privacy', 'Can my personal data be misused?', 'Как используются мои личные данные и данные о моем доме?'],
    help_privacy))

user_commands.update(
    dict.fromkeys(['🏠 New house', '🏠 Новый дом', '/NewHouse', '/newHouse', '/newhouse', '/New_House', '/new_house'],
                  go_to_new_house))
user_commands.update(dict.fromkeys(['👨‍👩‍👧‍👦 Share access', '👨‍👩‍👧‍👦 Общий доступ'], go_to_share_access))
user_commands.update(dict.fromkeys(['📶 New level', '📶 Новый этаж'], go_to_new_level))
user_commands.update(dict.fromkeys(['🚪 New room', '🚪 Новая комната'], go_to_new_room))
user_commands.update(dict.fromkeys(
    ['🆕 Create a new object here', '🆕 Create a new object in the room', '🆕 Create a new object in the cabin',
     '🆕 Create a new object in the closet', '🆕 Create a new object in the box', '🆕 Create a new object inside',
     '🆕 Создать новый объект здесь', '🆕 Создать новый объект в комнате', '🆕 Создать новый объект в шкафу',
     '🆕 Создать новый объект в ящике', '🆕 Создать новый объект в коробке', '🆕 Создать новый предмет внутри'],
    go_to_new_item))
user_commands.update(dict.fromkeys(['/search', '/Search', '🔍 Search', '🔍 Поиск'], go_to_search_by_name))
user_commands.update(dict.fromkeys(['/add_img', '📸 Add photo', '📸 Добавить фото'], go_to_add_img))
user_commands.update(dict.fromkeys(['/change_img', '📸 Change photo', '📸 Заменить фото'], go_to_change_img))
user_commands.update(dict.fromkeys(['/delete_img', '❌📸 Delete photo', '❌📸 Удалить фото'], go_to_delete_img))
user_commands.update(dict.fromkeys(
    ['/rename', '✍️Rename', '✍️Rename the house', '✍️Rename the level', '✍️Rename the room', '✍️Rename the cabin',
     '✍️Rename the closet', '✍️Rename the storage', '✍️Rename the box', '✍️Переименовать', '✍️Переименовать дом',
     '✍️Переименовать этаж', '✍️Переименовать комнату', '✍️Переименовать шкаф', '✍️Переименовать хранилище',
     '✍️Переименовать объект (хранилище)', '✍️Переименовать ящик', '✍️Переименовать коробку'], go_to_rename_item))
user_commands.update(dict.fromkeys(['/start', 'start'], step_start))
user_commands.update(dict.fromkeys(
    ['/move', '/take', '↪️Move the item', '↪️Move the room', '↪️Move the level', '↪️Move the cabin',
     '↪️Move the closet', '↪️Move the storage', '↪️Move the box', '↪️Переместить этот предмет', '↪️Переместить комнату',
     '↪️Переместить этаж', '↪️Переместить шкаф', '↪️Переместить хранилище', '↪️Переместить ящик',
     '↪️Переместить коробку'], go_to_take_item))
user_commands.update(dict.fromkeys(['/get_it_back'], get_it_back))
user_commands.update(
    dict.fromkeys(['/take_to_use', '🤷‍♀️Mark as missing 🤷‍♂️', '🤷‍♀️Нет на месте 🤷‍♂️'], go_to_take_to_use))
user_commands.update(
    dict.fromkeys(['/put_back', '🕵️‍♂️Item has been found', '🕵️‍♂️Отметить, что предмет найден'], go_to_put_back))
user_commands.update(dict.fromkeys(['/comment', '📝 Comment', '📝 Прокомментировать'], go_to_comment))
user_commands.update(dict.fromkeys(['/edit_comment', '📝 Edit comment', '📝 Изменить комментарий'], go_to_comment))
user_commands.update(dict.fromkeys(['/highlight', '☝️Highlight', '☝️Отметить как важное'], go_to_highlight))
user_commands.update(dict.fromkeys(['/unhighlight', '👇 De-emphasize', '👇 Убрать из важного'], go_to_unhighlight))
user_commands.update(dict.fromkeys(
    ['/delete', '/del', '❌ Delete', '❌ Delete the house', '❌ Delete the level', '❌ Delete the room',
     '❌ Delete the cabin', '❌ Delete the closet', '❌ Delete the storage', '❌ Delete the box', '❌ Delete the item',
     '❌ Удалить', '❌ Удалить этот предмет', '❌ Удалить дом', '❌ Удалить этаж', '❌ Удалить комнату', '❌ Удалить шкаф',
     '❌ Удалить хранилище', '❌ Удалить объект (хранилище)', '❌ Удалить ящик', '❌ Удалить коробку'], go_to_delete_item))
user_commands.update(dict.fromkeys(
    ['/change_emoji', '/update_emoji', '/changeemoji', '/updateemoji', '🤖 Change class & emoji',
     '🤖 Изменить класс или емодзи'], go_to_change_emoji))
user_commands.update(dict.fromkeys(
    ['/DomData', '/domData', '/domdata', 'My houses', '/myhouses', '/My_houses', 'Мои дома', '/Мои_дома', 'Мои_дома',
     'мои_дома', '/мои_дома'],
    go_top_level))

item_types_dic = dict.fromkeys(['Closet', 'Шкаф'], 'cupboard')
item_types_dic.update(dict.fromkeys(['Storage', 'Место хранения'], 'storage'))
item_types_dic.update(dict.fromkeys(['Box', 'Коробка'], 'box'))
item_types_dic.update(dict.fromkeys(['Item', 'Вещь'], 'item'))

item_classes_dic = dict.fromkeys(['Documents, books, magazines', 'Документы, книги, журналы'], 'paper')
item_classes_dic.update(dict.fromkeys(['Stationery', 'Концелярские товары'], 'stationery'))
item_classes_dic.update(dict.fromkeys(['CDs, tapes, flash cards', 'CD, кассеты, пленки'], 'infocarrier'))
item_classes_dic.update(dict.fromkeys(['Electronics', 'Техника'], 'tech'))
item_classes_dic.update(dict.fromkeys(['Tools and gear', 'Инструменты и комплектующие'], 'tools_and_gear'))
item_classes_dic.update(dict.fromkeys(['Clothes', 'Одежда'], 'clothes'))
item_classes_dic.update(dict.fromkeys(['Sport', 'Спорт'], 'sport'))
item_classes_dic.update(dict.fromkeys(['Music', 'Музыка'], 'music'))
item_classes_dic.update(dict.fromkeys(['Toys', 'Игрушки'], 'toys'))
item_classes_dic.update(dict.fromkeys(['Food', 'Еда'], 'food'))
item_classes_dic.update(dict.fromkeys(['Tableware', 'Посуда'], 'tableware'))
item_classes_dic.update(dict.fromkeys(['Plant', 'Растение'], 'plant'))
item_classes_dic.update(dict.fromkeys(['etc', 'Другое'], 'etc'))

random_stickers = ["CAADAgADFgADwDZPE2Ah1y2iBLZnFgQ", "CAADAgADCwADlp-MDpuVH3sws_a7FgQ",
                   "CAADAgADEgADWbv8JfBCObndTSUaFgQ",
                   "CAADAgADcQAD9wLID3kKxPT9t4jLFgQ", "CAADAgADpAADMNSdEU7MT7Gv4LoZFgQ",
                   "CAADAgAD8AEAAsoDBgtTNPb4vSaRRxYE",
                   "CAADAgADEgADO2AkFBf2ezO6T5XEFgQ", "CAADAgAD9wADVp29CgtyJB1I9A0wFgQ",
                   "CAADAgADpwADFkJrCtlzNEqUNHMpFgQ",
                   "CAADAgAD9QIAArVx2gam8H9Dr5OR_xYE", "CAADAgADswADMNSdET9j0fISlCKpFgQ",
                   "CAADAgADfgADlp-MDnGDEZ4sXLblFgQ",
                   'CAACAgIAAxkBAAIV_V_hG6ZPIIzPNN3VIqE2ewwnH01iAAL7AANSiZEjHEzYB3L4zKweBA',
                   'CAACAgIAAxkBAAIWFl_hH0JnLlOP3wO6LgABVRhNXLLFfwAC9wADUomRI6J6Ym0_4ftHHgQ']

random_belarus_stickers = ['CAACAgIAAxkBAAIV_V_hG6ZPIIzPNN3VIqE2ewwnH01iAAL7AANSiZEjHEzYB3L4zKweBA',
                           'CAACAgIAAxkBAAIWFl_hH0JnLlOP3wO6LgABVRhNXLLFfwAC9wADUomRI6J6Ym0_4ftHHgQ']


emoji_dic = myfiles.open_categories('emoji.txt', ':')
special_topics_dic = myfiles.open_categories('special_topics.txt')


def start_polling(b):

    while True:
        try:
            b.polling(none_stop=True)
            logger.info("Started polling")
        except ConnectionError as error:
            logger.info(f"Can't start polling. Connection error: {error}")
            time.sleep(5)
        except Exception as error:
            error_msg = f"Can't start polling. Error: {error}"
            logger.info(error_msg)
            send_msg_to_developer(error_msg)
            if 'NoneType' in str(error):
                time.sleep(50)
            time.sleep(30)


formIbase(ibase)

start_polling(bot)