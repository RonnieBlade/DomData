import os
import time
import emoji

import mylogger
import io
from PIL import Image
import requests
from datetime import datetime
from config_reader import read_config

logger = mylogger.get_logger(__name__)



full_url_to_img_storage = read_config("config.ini", "ftp")['full_url']
temp_img_dir = read_config("config.ini", "files")['temp_img_dir']


def open_categories(path, add_text_at_start_and_end='', to_lower=True):
    emoji_dic = dict()
    for category in open_categories_file(path, add_text_at_start_and_end, to_lower):
        emoji_dic.update(category)

    return emoji_dic


def open_categories_file(path, add_text_at_start_and_end, to_lower=True):
    with open(path, encoding='utf-8', mode='r') as f:
        emoji_key = None
        values = []
        for x in f:
            x = x.strip()
            if to_lower:
                x = x.lower()
            if x.startswith("*"):
                if emoji_key is not None:
                    yield {emoji_key: values}
                    values = []
                emoji_key = x[1:]
                continue
            if x != '':
                values.append(emoji.emojize(f"{add_text_at_start_and_end}{x}{add_text_at_start_and_end}", use_aliases=True))
        # Don't forget to add the last category
        yield {emoji_key: values}


def resize_img(image, min_size):

    img = Image.open(io.BytesIO(image))

    horizontal = True
    if img.size[1] > img.size[0]:
        horizontal = False

    if horizontal:
        hpercent = (min_size / float(img.size[1]))
        wsize = int((float(img.size[0]) * float(hpercent)))
        img = img.resize((wsize, min_size), Image.ANTIALIAS)
    else:
        wpercent = (min_size / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((min_size, hsize), Image.ANTIALIAS)

    imgByteArr = io.BytesIO()
    img.save(imgByteArr, format='jpeg')
    imgByteArr = imgByteArr.getvalue()

    return imgByteArr


def download_pic(id):
    url = f"{full_url_to_img_storage}/item_{id}.jpg"
    myfile = requests.get(url)
    if myfile.status_code == 404:
        return None
    path = os.path.join(temp_img_dir, f'item_{id}.jpg')
    open(path, 'wb').write(myfile.content)
    return path


def save_pic(message, instname, bot, resize=False, new_size=None):
    done = False
    tries = 0
    while not done and tries < 3:
        try:
            logger.info(f'message.photo = {message.photo}')
            fileID = message.photo[-1].file_id
            logger.info(f'fileID = {fileID}')
            file_info = bot.get_file(fileID)
            logger.info(f'file.file_path = {file_info.file_path}')
            downloaded_file = bot.download_file(file_info.file_path)

            if resize:
                downloaded_file = resize_img(downloaded_file, new_size)

            if not os.path.isdir(temp_img_dir):
                os.mkdir(temp_img_dir)

            with open(os.path.join(temp_img_dir, f"{instname}.jpg"), "wb") as new_file:
                new_file.write(downloaded_file)
            done = True
            return True
        except Exception as error:
            logger.exception('An error occurred while saving file Error:', error)
            tries += 1
            time.sleep(5)
    return False


def delete_temp_pic(instname):
    try:
        os.remove(os.path.join(temp_img_dir, f"{instname}.jpg"))
        logger.debug("Removed a temporary file")
        return True
    except EnvironmentError as error:
        logger.exception(f"Can't remove temp file. Error: {error}")
        return False


def delete_file(path):
    try:
        os.remove(path)
        logger.debug("Deleted a temp file")
        return True
    except EnvironmentError as error:
        logger.exception(f"Can't remove temp file. Error: {error}")
        return False


def save_request_to_file(user_name, txt, file_path):
    if len(file_path) > 1:
        if not os.path.isdir(file_path[0]):
            os.mkdir(file_path[0])

    with open(os.path.join(*file_path), "a", encoding="utf-8") as f:
        now = datetime.now().strftime("%Y.%m.%d, %H:%M:%S")
        f.write(f"{now} User {user_name}:\n{txt}\n\n")
