import asyncio
import json
import emoji
import randtext as rt
import mylogger
import db.mydb as mydb
from datetime import datetime, timedelta
from translater import t

from utility import keyboard

logger = mylogger.get_logger(__name__)

# resolutions for standard and premium users
item_pic_resolution = 400
item_pic_resolution_premium = 720
storage_pic_resolution = 600
storage_pic_resolution_premium = 900

all_item_fields = "id, name, location, type, last_move_date, dom_id, item_class, item_emoji, user_id, has_img, tags, file_id, taken_by_user, last_taken_date, comment, commented_by_user, comment_date, wish_status, wished_by_user, wish_date, purchased_by_user, purchase_date, highlighted_by, highlighted_date, tagged_by, tags_date, demo_role"


class Item:
    def __init__(self, my_id, name, location, my_type=None, date=None, dom_id=0, item_class=None, item_emoji=None, user_id = 0, has_img=False, tags=None, file_id=None, space=None, taken_by_user=None, last_taken_date=None, comment=None, commented_by_user=None, comment_date=None, wish_status=None, wished_by_user=None, wish_date=None, purchased_by_user=None, purchase_date=None, highlighted_by=None, highlighted_date=None, tagged_by=None, tags_date=None, demo_role=None):
        self.name = name
        self.id = my_id
        self.location = location

        # immutable
        self.type = my_type
        self.date = date
        self.user_id = user_id
        self.demo_role = demo_role

        self.dom_id = dom_id
        self.item_class = item_class
        self.item_emoji = None
        self.file_id = file_id
        self.taken_by_user = taken_by_user
        self.last_taken_date = last_taken_date

        self.dom_missing_things = []
        self.dom_highlighted_things = []

        self.comment = comment
        self.commented_by_user = commented_by_user
        self.comment_date = comment_date

        # not implemented yet
        self.wish_status = wish_status
        self.wished_by_user = wished_by_user
        self.wish_date = wish_date
        self.purchased_by_user = purchased_by_user
        self.purchase_date = purchase_date

        self.highlighted_by = highlighted_by
        self.highlighted_date = highlighted_date

        self.id64 = str(my_id)

        self.tagged_by = tagged_by
        self.tags_date = tags_date

        self.tags = None
        if tags is not None:
            if type(tags) == str:
                self.tags = json.loads(tags)
            else:
                self.tags = tags

        if has_img is not None and has_img == 1:
            self.has_img = True
        else:
            self.has_img = False

        if item_emoji is not None and item_emoji != "":
            self.item_emoji = emoji.emojize(f":{item_emoji}:", use_aliases=True)

        if space is None:
            self.space = []
        else:
            self.space = space

        # Check if can put an item here
    def can_i_put_it_here(self, item_in_hands):

        loc_type = self.type
        item_type = item_in_hands.type

        if loc_type == "item" and item_type != "item":
            return False
        if loc_type == "box" and item_type not in {"box", "item"}:
            return False
        if loc_type in {"storage", "cupboard"} and item_type not in {"storage", "box", "item"}:
            return False
        if loc_type == "room" and item_type not in {"cupboard", "storage", "box", "item"}:
            return False
        if loc_type == "level" and item_type != "room":
            return False
        if loc_type in {"house", "dom"} and item_type not in {"level", "room"}:
            return False
        return True

    def count_items_inside(self, first=False):
        emojies = []
        count = 1

        # Not considering houses, floors, rooms as items to count
        if self.item_class in ['house', 'dom', 'level', 'room'] or first:
            count = 0

        if len(self.space) == 0:
            if self.item_emoji is not None and self.item_emoji != "" and self.item_class not in {'house', 'dom',
                                                                                                 'level',
                                                                                                 'room', 'cupboard',
                                                                                                 'storage', 'box'}:
                emojies.append(self.item_emoji)
            return [count, emojies]
        else:
            for it in self.space:
                res = it.count_items_inside()
                count = count + res[0]
                emojies.extend(res[1])

            if count < 0:
                pass

            return [count, emojies]

    async def update_and_form_reply(self, user, atr, value, auto=False):

        asyncio.create_task(mydb.update_item("dom", "id", atr, value, self.id))

        reply = ""

        if atr == "demo_role":
            # no reply needed
            return
        if atr == "file_id":
            self.file_id = value
            # no reply needed
            return
        if atr == "tags":
            # no reply needed
            return
        if atr == "tagged_by":
            self.tagged_by = value
            # no reply needed
            return
        if atr == "tags_date":
            # no reply needed
            return
        if atr == "dom_id":
            self.dom_id = value
            # no reply needed
            return
        if atr == "location":
            self.location = value
            self.date = datetime.now()
            asyncio.create_task(mydb.update_item("dom", "id", "last_move_date", self.date, self.id))
            # no reply needed
            return
        if atr == "taken_by_user":
            self.taken_by_user = value
            self.last_taken_date = datetime.now()
            asyncio.create_task(mydb.update_item("dom", "id", "last_taken_date", self.last_taken_date, self.id))
            # no reply needed
            return
        if atr == "highlighted_by":
            self.highlighted_by = value
            self.highlighted_date = datetime.now()
            asyncio.create_task(mydb.update_item("dom", "id", "highlighted_date", self.highlighted_date, self.id))
            # no reply needed
            return
        if atr == "has_img":
            self.has_img = value
            if value:
                reply = f"{t('pic_of', user)} *{self.name}* {t('is_uploaded', user)}"
            else:
                reply = f"{t('pic_of', user)} *{self.name}* {t('is_deleted', user)}"
        elif atr == "name":
            if self.type in {"house", "dom"}:
                asyncio.create_task(mydb.update_item("doms", "id", atr, value, self.dom_id))
            old_name = self.name
            self.name = value
            reply = f"*{old_name}* {t('renamed_to', user)} *{value}*"
        elif atr == "comment":

            self.comment = value
            self.commented_by_user = user.id

            if auto:
                self.commented_by_user = 1

            self.comment_date = datetime.now()
            asyncio.create_task(mydb.update_item("dom", "id", "commented_by_user", self.commented_by_user, self.id))
            asyncio.create_task(mydb.update_item("dom", "id", "comment_date", self.comment_date, self.id))

            if not auto:
                if value is None:
                    reply = f"{t('item_comment_deleted', user)}"
                else:
                    reply = f"{t('the_object', user)} *{self.name}* {t('item_commented', user)}"
            else:
                return reply

        elif atr == "item_class":

            if self.item_class is not None:
                old_class_str = self.item_class
                if value == old_class_str:
                    reply = f"{t('class_remains', user)} *{t(value, user).lower()}*"
                else:
                    reply = f"{t('class_changed', user)} {t('from', user)} *{t(old_class_str, user).lower()}* {t('to', user)} *{t(value, user).lower()}*"
            else:
                reply = f"{t('class_changed', user)} {t('to', user)} *{t(value, user).lower()}*"
            self.item_class = value
        elif atr == "item_emoji":
            new_emoji = emoji.emojize(f":{value}:", use_aliases=True)
            if value is None or value == "None":
                new_emoji = None
                reply = f"{t('emoji_removed', user)}"
            else:
                if self.item_emoji is not None:
                    old_emoji_str = self.item_emoji
                    reply = f"{t('emoji_changed', user)} {t('from', user)} {old_emoji_str} {t('to', user)} {new_emoji}"
                else:
                    reply = f"{t('emoji_changed', user)} {t('to', user)} {new_emoji}"
            self.item_emoji = new_emoji

        return reply

    @staticmethod
    def tags_prepare(tags, count):
        if tags is None:
            return None
        new_tags = tags[:count]
        new_tags_new_format = []
        for t in new_tags:
            tag = {"c": round(t.get("confidence"), 2), "tag": t.get("tag").get("en")}
            new_tags_new_format.append(tag)
        return new_tags_new_format

    @staticmethod
    def newItemFromDB(it):
        return Item(it[0], it[1], it[2], it[3], it[4], it[5], it[6], it[7], it[8], it[9], it[10], it[11], None, it[12],
                    it[13], it[14], it[15], it[16], it[17], it[18], it[19], it[20], it[21], it[22], it[23], it[24],
                    it[25],
                    it[26])


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


def find_item_dom(item, user, items):
    if item.location == 0:
        return item
    else:
        parent = find_item_by_id(item.location, items, user)
        return find_item_dom(parent, user, items)


def add_missing_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_missing_things = [it for it in item_dom.dom_missing_things if it.id != item.id]
    item_dom.dom_missing_things.append(item)


def add_highlighted_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_highlighted_things = [it for it in item_dom.dom_highlighted_things if it.id != item.id]
    item_dom.dom_highlighted_things.append(item)


def remove_missing_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_missing_things = [it for it in item_dom.dom_missing_things if it.id != item.id]


def remove_highlighted_thing(item, user, items):
    item_dom = find_item_dom(item, user, items)
    item_dom.dom_highlighted_things = [it for it in item_dom.dom_highlighted_things if it.id != item.id]


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


def get_items(user, items, ibase):
    if user.loading:
        return

    user.loading = True

    user.houses = []
    temp_houses = user.get_user_houses()

    # if the user doesn't have rights to any house, then leave
    if len(temp_houses) == 0:
        user.loading = False
        return

    for h in temp_houses:
        user.houses.append(h[0])

    things_from_base = mydb.get_everything([all_item_fields, "dom"], user.houses)

    # refresh ibase
    ibase.delete_user_items(items, user)

    for it in things_from_base:
        item = Item.newItemFromDB(it)

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


class Step:
    def __init__(self, name, location=0):
        self._name = name
        self._location = location
        self.new_item_name = ""
        self.new_item_type = ""
        self.new_item_class = ""
        self.sharing_access_key = None
        self.new_item_with_photo = False
        self.new_item_tags = []
        self.temp_item_tags = []
        self.new_item_emoji_str = ""

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value


class UserAction:
    def __init__(self, atype='user_msg', content=None, status='request'):
        self.date = datetime.now()
        self.atype = atype
        self.content = content
        self.status = status


class User:
    def __init__(self, id, name=None, step=Step("start"), lang=None, activated=True, premium=False, admin=False):
        self.id = id
        self.name = name
        self.step = Step(step)
        self.lang = lang
        self.dom = []
        self.houses = set()

        if premium is not None and premium == 1:
            self.premium = True
        else:
            self.premium = False
        if admin is not None and admin == 1:
            self.admin = True
        else:
            self.admin = False

        self.item_in_hands = None
        self.item_in_hands_put_but_text = None

        self.items_dic = {}

        self.loading = False

        self.action_logs = []

        self.busy = False

        self.last_take_item_location = None
        self.last_put_item_location = None

        self.last_use_date = datetime.now()

        asyncio.run(self.update_use_date_in_db())

        self.activated = activated

    def get_and_add_unique_key(self):
        key = rt.get_random_string(32)
        db_reply = mydb.check_is_ok(key)
        if db_reply[1]:
            mydb.add_access_key(self, key)
            return key

    def get_appropriate_resolution(self):
        if self.step.new_item_type == 'item':
            resolution = item_pic_resolution
            if self.premium:
                resolution = item_pic_resolution_premium
        else:
            resolution = storage_pic_resolution
            if self.premium:
                resolution = storage_pic_resolution_premium

        return resolution

    def clear_new_item_info(self):
        self.step.new_item_name = ""
        self.step.new_item_type = ""
        self.step.new_item_class = ""
        self.step.new_item_with_photo = False
        self.step.new_item_tags = []
        self.step.temp_item_tags = []
        self.step.new_item_emoji_str = ""

    def get_user_houses(self):
        keys = mydb.get_user_keys(self.id)
        houses = mydb.get_user_houses_by_key(keys)
        return houses

    async def update_use_date_in_db(self):
        asyncio.create_task(mydb.update_use_date(self))

    def update_use_date(self):
        if self.last_use_date < datetime.now() - timedelta(hours=1):
            asyncio.run(self.update_use_date_in_db())
            self.last_use_date = datetime.now()

    def check_limit(self, atype, delta, limit, complete=False):
        actions = list(
            filter(lambda r: r.date > datetime.now() - delta and r.atype == atype, self.action_logs))
        if complete:
            actions = list(
                filter(lambda r: r.status == 'complete', actions))
        if len(actions) > limit:
            return False
        else:
            return True

    def new_action(self, atype='user_msg', content=None, status='request'):

        if self.premium:
            msg_sec = 0
            msg_min = 60
            new_item_3hours = 150
            new_img_6hours = 150
            imagga_6hours = 120
            imagga_1hour = 50
            new_house_1hour = 10
            demo_house_12hours = 10
        else:
            msg_sec = 0
            msg_min = 20
            new_item_3hours = 50
            new_img_6hours = 25
            imagga_6hours = 50
            imagga_1hour = 15
            new_house_1hour = 3
            demo_house_12hours = 3

        if content is None:
            content_str = ''
        else:
            content_str = f'\nContent: {content}'

        logger.debug(f'User {self.name} - new action\nType: {atype}{content_str}')

        self.action_logs = list(
            filter(lambda r: (r.date > datetime.now() - timedelta(minutes=3) and r.atype == 'user_msg') or (r.atype != 'user_msg' and r.date > datetime.now() - timedelta(hours=12)), self.action_logs))

        ok = True

        if status == 'request':
            # fast msgs limit
            if atype == 'user_msg':
                ok = self.check_limit('user_msg', timedelta(seconds=0.5), msg_sec)
                if not ok:
                    return False
                ok = self.check_limit('user_msg', timedelta(minutes=1), msg_min)
            if atype == 'new_item':
                ok = self.check_limit('new_item', timedelta(hours=3), new_item_3hours, complete=True)
            if atype == 'new_img':
                ok = self.check_limit('new_img', timedelta(hours=6), new_img_6hours, complete=True)
            if atype == 'imagga':
                ok = self.check_limit('imagga', timedelta(hours=6), imagga_6hours, complete=True)
                if not ok:
                    return False
                ok = self.check_limit('imagga', timedelta(hours=1), imagga_1hour, complete=True)
            if atype == 'new_house':
                ok = self.check_limit('new_house', timedelta(hours=1), new_house_1hour, complete=True)
            if atype == 'demo_house':
                ok = self.check_limit('demo_house', timedelta(hours=12), demo_house_12hours, complete=True)

        if not ok:
            return False

        self.action_logs.append(UserAction(atype, content, status))
        return True

    # variable to store 'what generators return'
    generator_return = None

    def set_user_status(self, users, txt, status, status_value=True):
        try:
            user_id = int(txt.split()[1])
            success = mydb.update_user_status(user_id, status, status_value)

            if not success:
                yield self.id, f"User {user_id} not found or wasn't changed"
                return

            loaded_user = next((x for x in users if x.id == user_id), None)
            if loaded_user is not None:
                if status == 'admin':
                    loaded_user.admin = status_value
                    yield self.id, f'Status {status} = {status_value} set for {loaded_user.name}'
                if status == 'premium':
                    loaded_user.premium = status_value
                    if status_value:
                        yield user_id, t('premium_version_activated', loaded_user)
                    yield self.id, f'Status {status} = {status_value} set for {loaded_user.name}'

            self.generator_return = True
        except Exception as exp:
            logger.error(f"Can't set user status {status}: {txt}, exception: {exp}")
            self.generator_return = False

    def offer_user_name_variants(self):
        reply = t("choose_name_from_tags", self)

        tags = self.step.temp_item_tags[:10]
        my_keyboard = []
        for tag in tags:
            but = tag.get("tag").get(self.lang)
            if but not in my_keyboard:
                my_keyboard.append(but)

        my_keyboard.append(t("cancel", self))
        yield self.id, reply, keyboard(my_keyboard)

        self.step.name = "new_item"

    # To avoid showing enormous crazy numbers in items IDs
    # let's create individual IDs especially for the user
    user_item_last_id = 1

    def update_dic(self, item_id):
        if item_id not in self.items_dic.keys():
            self.items_dic.update({item_id: self.user_item_last_id})
            self.user_item_last_id += 1

    @staticmethod
    def format_id(v):
        v_str = str(v)
        while len(v_str) < 3:
            v_str = '0' + v_str
        return v_str

    @staticmethod
    def reformat_id_from_str(v):
        v = str(v)
        while v[0] == '0':
            v = v[1:]
        return int(v)

    def id_conv(self, item_id, from_id_to_personal_id=True):
        try:
            item_id = int(item_id)
        except Exception:
            return None

        if item_id in {0, -1}:
            return item_id

        if from_id_to_personal_id:
            if item_id in self.items_dic.keys():
                return User.format_id(self.items_dic.get(item_id))
            else:
                self.update_dic(item_id)
                self.id_conv(item_id)
        else:
            if item_id not in {0, -1}:
                item_id = User.reformat_id_from_str(item_id)
            listOfKeys = [key for (key, value) in self.items_dic.items() if value == item_id]
            if len(listOfKeys) != 0:
                return listOfKeys[0]
            else:
                return None


class AllItemsList:
    '''List of Item objects wrapper class
    on condition of all elements id uniqueness
    when adding via append, implemented for searching inside the house'''

    def __init__(self, values=None):
        if values is None:
            self.values = []
        else:
            self.values = values

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        if any(x.id == key for x in self.values):
            return next((x for x in self.values if x.id == key), None)
        else:
            return None

    def append(self, v):
        if not any(x.id == v.id for x in self.values):
            self.values.append(v)

    def remove_by_dom(self, i):
        self.values = list(filter(lambda item: item.dom_id != i, self.values))

    def remove_by_id(self, i):
        self.values = list(filter(lambda item: item.id != i, self.values))

    # used to refresh
    def delete_user_items(self, dom, user):
        temp_dom = list(dom)

        for d in temp_dom:
            if d.dom_id in user.houses:
                self.remove_by_dom(d.dom_id)
                dom.remove(d)

    def form_Ibase(self, dom):
        things_from_base = mydb.get_items_for_ibase([all_item_fields, "dom"])

        for it in things_from_base:
            item = Item.newItemFromDB(it)
            self.append(item)
            # adding houses in global dom
            if item.type in {'dom', 'house'}:
                dom.append(item)



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


def get_dir(id, items, user, by_user=False):
    item = find_item_by_id(id, items, user, by_user)

    if id == 0:
        top = True
        filtered_items = list(items)
        filtered_items = list(filter(lambda item: item.dom_id in user.houses, filtered_items))
        for fi in filtered_items:
            user.update_dic(fi.id)
        item = Item(0, f"{t('my_doms', user)}", -1, "top", datetime.now(), 0, None, None, 0, None, None, None,
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
