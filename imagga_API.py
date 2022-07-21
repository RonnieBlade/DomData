import json
import random
import threading
import time

import requests
import mylogger

import db.mydb as mydb

from config_reader import read_config

from datetime import datetime, timedelta

logger = mylogger.get_logger(__name__)

key_n = 0

conf = read_config("config.ini", "imagga")

stats = mydb.get_imagga_usage_list()

class ImaggaUser:
    def __init__(self, key, secret, proxy=None, port=None, prx_user=None, prx_password=None):

        if proxy == '':
            proxy = None
            port = None
            prx_user = None
            prx_password = None

        self.stats = list(
            filter(lambda r: r['api_key'] == key and r['date'] > datetime.now() - timedelta(days=31), stats))

        self.api_key = key
        self.api_secret = secret

        self.proxy_ip = proxy
        self.proxy_port = port
        self.proxy_user = prx_user
        self.proxy_pass = prx_password

        # Proxy authorization works only through http
        self.proxies = {'http': f'http://{self.proxy_user}:{self.proxy_pass}@{self.proxy_ip}:{self.proxy_port}'}


def load_imagga_users():
    imagga_users = []

    jdata = json.loads(conf['imagga_users'])
    for d in jdata:
        user = ImaggaUser(**d)
        imagga_users.append(user)
    return imagga_users


imagga_users = load_imagga_users()


def get_image_tags(user, img_path):

    error_occured = False
    try_n = 0

    lang = "en"
    if user.lang != "en":
        lang = f"{user.lang}," + lang

    while True:

        if try_n > random.randint(5, 8):
            return None

        for u in imagga_users:
            u.stats = list(
                filter(lambda r: r['date'] > datetime.now() - timedelta(days=31), u.stats))

        num = 0

        while len(imagga_users[
                      num].stats) > random.randint(100, 200) and num + 1 < len(
                imagga_users):
            num += 1

        if num >= len(imagga_users) or error_occured:
            num = random.randint(0, len(imagga_users) - 1)

        iuser = imagga_users[num]

        try:

            if iuser.proxy_ip is None:
                response = requests.post(
                    'https://api.imagga.com/v2/tags',
                    auth=(iuser.api_key, iuser.api_secret),
                    params={'language': lang},
                    files={'image': open(img_path, 'rb')})
            else:
                response = requests.post(
                    'https://api.imagga.com/v2/tags',
                    auth=(iuser.api_key, iuser.api_secret),
                    params={'language': lang},
                    files={'image': open(img_path, 'rb')}, proxies=iuser.proxies)

            resp = response.json()

            iuser.stats.append({'api_key': iuser.api_key, 'date': datetime.now()})
            ta = threading.Thread(target=lambda: mydb.add_imagga_use(iuser.api_key, str(response), user.id))
            ta.start()

            tags = resp.get("result").get("tags")
            return tags
        except Exception as er:
            error_occured = True
            try_n += 1
            logger.error("can't connect to imagga", er)
            time.sleep(random.randint(2, 5))
