import json
import threading

import emoji
from nsc import dec_to_base

import mylogger

import db.mydb as mydb

from datetime import datetime, timedelta

logger = mylogger.get_logger(__name__)


class Item:
    def __init__(self, my_id, name, location, my_type=None, date=None, dom_id=0, item_class=None, item_emoji=None, user_id = 0, has_img=False, tags=None, file_id=None, space=None, taken_by_user=None, last_taken_date=None, comment=None, commented_by_user=None, comment_date=None, wish_status=None, wished_by_user=None, wish_date=None, purchased_by_user=None, purchase_date=None, highlighted_by=None, highlighted_date=None, tagged_by=None, tags_date=None, demo_role=None):
        self.name = name
        self.id = my_id
        self.location = location
        self.type = my_type
        self.date = date
        self.dom_id = dom_id
        self.item_class = item_class
        self.item_emoji = None
        self.user_id = user_id
        self.file_id = file_id
        self.taken_by_user = taken_by_user
        self.last_taken_date = last_taken_date

        self.demo_role = demo_role

        self.dom_missing_things = []
        self.dom_highlighted_things = []

        self.comment = comment
        self.commented_by_user = commented_by_user
        self.comment_date = comment_date
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




class Step:
    def __init__(self, name, location=0):
        self.name = name
        self.location = location
        self.new_item_name = ""
        self.new_item_type = ""
        self.new_item_class = ""
        self.sharing_access_key = None
        self.new_item_with_photo = False
        self.new_item_tags = []
        self.temp_item_tags = []
        self.new_item_emoji_str = ""


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

        self.update_use_date_in_db()

        self.activated = activated

    def update_use_date_in_db(self):
        ta = threading.Thread(target=lambda: mydb.update_use_date(self))
        ta.start()

    def update_use_date(self):
        if self.last_use_date < datetime.now() - timedelta(hours=1):
            self.update_use_date_in_db()
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

    def update_dic(self, item_id):
        if item_id not in self.items_dic.keys():
            v = 1
            while v in self.items_dic.values():
                v = v + 1
            self.items_dic.update({item_id: v})

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
