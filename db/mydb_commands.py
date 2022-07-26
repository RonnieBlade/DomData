from mysql.connector import MySQLConnection, Error
from config_reader import read_config
import time
import mylogger

logger = mylogger.get_logger(__name__)

# seconds to wait when error occurred before trying again
wait_time = 5


def connect():
    """ Connect to MySQL database """

    done = False
    db_config = read_config()

    while not done:
        try:
            logger.debug('Connecting to MySQL database...')
            conn = MySQLConnection(**db_config)

            if conn.is_connected():
                logger.debug('connection established.')
                done = True
            else:
                logger.warning('connection failed. try again i 5 secs')
                time.sleep(wait_time)

        except Error as error:
            logger.exception(error)
            logger.exception('Connection closed. try again i 5 secs')
            time.sleep(wait_time)

    return conn


def close (conn):
    done = False
    while not done:
        try:
            if conn.is_connected():
                conn.close()
                logger.debug('Connection closed.')
            else:
                logger.warning('Connection was already closed.')

            done = True

        except Error as error:
            logger.exception(error)
            time.sleep(wait_time)


# returns one value
def read_one_value(db, query, args):
    return execute(db, query, args, False, False, True)


# returns one row tuple
def read_one_row(db, query, args):
    return execute(db, query, args)


def read_all(db, query, args):
    return execute(db, query, args, False, True)


def write(db, query, args, return_rowcount=False):
    return execute(db, query, args, True, return_rowcount=return_rowcount)


def execute(db, query, args, do_write=False, fetchall=False, single_value=False, return_rowcount=False):
    done = False
    while not done:
        try:
            if not db.is_connected():
                logger.warning('no connection with DB - reconnect')
                db = connect()
        except Error as error:
            logger.warning('Error occurred while checking connection with DB - reconnect')
            logger.warning(error)
            db = connect()

        try:
            cur = db.cursor()
            cur.execute(query, args)
            done = True
            if do_write:
                db.commit()
                # if writes - returns last id
                if return_rowcount:
                    return cur.rowcount
                return cur.lastrowid
            else:
                if single_value:
                    return cur.fetchone()[0]
                if fetchall:
                    return cur.fetchall()
                else:
                    return cur.fetchone()

        except Error as error:
            logger.exception('Error occurred while executing command - start again')
            logger.exception(error)
            time.sleep(wait_time)


if __name__ == '__main__':
    connect()
