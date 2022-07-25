import os
from ftplib import FTP, error_perm
import time
from config_reader import read_config
import mylogger
import myfiles

logger = mylogger.get_logger(__name__)

wait_time = 5

ftp_config = read_config("config.ini", "ftp")
temp_img_dir = read_config("config.ini", "files")['temp_img_dir']

def connnect():

    ftp_config = read_config("config.ini", "ftp")
    try_n = 0

    while True:
        try:
            ftp = FTP(ftp_config['host'])
            ftp.login(ftp_config['user'], ftp_config['passwd'])
            return ftp
        except Exception as error:

            if try_n >= 1:
                logger.exception('FTP connection failed. Return None')
                return None
            logger.exception('FTP connection failed. try again in 5 secs')
            time.sleep(wait_time)
            try_n += 1


# upload or delete
def upload_img(picname, new_pic_name, delete_file=False):

    ftp = connnect()

    if ftp is None:
        return None

    ok = False
    while not ok:
        try:
            ftp.cwd(ftp_config['path'])
            data = ftp.retrlines('LIST')
            ok = True
        except Exception as ex:
            logger.exception('ftp.retrlines failed', ex)
            time.sleep(5)

    path = os.path.join(temp_img_dir, f"{picname}.jpg")

    if not delete_file:
        file = open(path, "rb")  # file to send
    else:
        file = None

    done = False
    tries = 0

    while not done and tries < 10:
        try:
            if delete_file:
                ftp.delete(f"{new_pic_name}.jpg")  # delete the file
            else:
                ftp.storbinary(f"STOR {new_pic_name}.jpg", file)  # send the file
            done = True
        except error_perm:
            tries = 10
            logger.exception('FTP transition failed. Permanent error')
        except Exception as error:
            tries += 1
            logger.exception('FTP transition failed. try again in 5 secs')
            time.sleep(wait_time)

    if not delete_file:
        try:
            file.close()  # close file
        except Exception as error:
            logger.exception('file.close failed')

    try:
        ftp.quit()  # close FTP
    except Exception as error:
        logger.exception('ftp.quit()  failed')

    if not done:
        return False

    return True