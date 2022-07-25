import datetime
import json
from db import mydb_commands
import mylogger

logger = mylogger.get_logger(__name__)


def get_everything(inf, doms):

    query = f"SELECT {inf[0]} FROM {inf[1]} WHERE (dom_id) in (%s"
    lis = []
    count = 0
    for d in doms:
        lis.append(int(d))
        if count != 0:
            query = query + ", %s"
        count = count + 1
    query = query + ")"

    args = tuple(lis)

    logger.info("Getting everything")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)
    return res


def get_items_for_ibase(inf):

    query = f"SELECT {inf[0]} FROM {inf[1]} WHERE type = 'dom' or (type = 'item' and demo_role is null) order by date desc limit 5000"

    logger.info("Getting items for ibase")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, {})
    mydb_commands.close(db)
    return res


def get_user_keys(id):

    query = f"SELECT mykey FROM access WHERE telegram_id = {id}"

    logger.info("Getting user keys")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, {})
    mydb_commands.close(db)
    return res


def get_dom_access_key(myid):

    db = mydb_commands.connect()
    query = "SELECT mykey FROM doms WHERE id = %s"
    args = (myid,)
    mykey = mydb_commands.read_one_value(db, query, args)

    mydb_commands.close(db)

    logger.info(f"Getting the keys for the house {myid} from database")

    return mykey


def get_user_houses_by_key(keys):

    if keys is None or len(keys) == 0:
        return []

    query = f"SELECT id FROM doms WHERE (mykey) in (%s"

    lis = []
    count = 0
    for s in keys:
        lis.append(''.join(s))
        if count != 0 :
            query = query + ", %s"
        count = count + 1
    query = query + ")"

    args = tuple(lis)

    logger.info("Getting user houses")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)
    return res


def get_user_ids_having_the_key(mykey):

    query = f"SELECT telegram_id FROM access WHERE mykey = %s"

    args = (mykey,)

    logger.info("Getting user ids having the key")

    db = mydb_commands.connect()

    res = mydb_commands.read_all(db, query, args)

    ids_list = []
    for r in res:
        ids_list.append(r[0])

    mydb_commands.close(db)
    return ids_list


def get_user(telegram_id):

    query = f"SELECT telegram_id, name, lang, premium, admin FROM users WHERE telegram_id = %s"

    args = (telegram_id,)

    logger.info("Getting user")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)

    if len(res) == 0:
        res = None
    else:
        res = res[0]

    return res


def get_imagga_usage_list():

    period = '31'

    query = "SELECT api_key, date FROM imagga_usage where date > now() - INTERVAL %s DAY"

    stats = []
    args = (period,)

    logger.info("Getting IMAGGA stats list")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)

    for u in res:
        stats.append({'api_key' : u[0], 'date': u[1]})

    return stats


def get_imagga_usage():

    period = '1 MONTH'

    query = "SELECT api_key, count(*) FROM imagga_usage where date > now() - INTERVAL %s group by api_key"

    stats = []
    args = (period)

    logger.info("Getting IMAGGA stats")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)

    for u in res:
        stats.append({'api_key' : u[0], 'count': u[1]})

    return stats


def get_users(ids):

    query = f"SELECT telegram_id, name, lang, premium FROM users WHERE (telegram_id) in (%s"

    lis = []
    count = 0
    for s in ids:
        lis.append(''.join(str(s)))
        if count != 0 :
            query = query + ", %s"
        count = count + 1
    query = query + ")"

    args = tuple(lis)

    logger.info("Getting users")

    db = mydb_commands.connect()
    res = mydb_commands.read_all(db, query, args)
    mydb_commands.close(db)

    users_list = []
    for u in res:
        users_list.append(User(u[0], u[1], "start", u[2], premium=u[3], admin=u[4]))

    return users_list


def update_user_status(user_id, status, status_value):
    db = mydb_commands.connect()

    if status_value:
        status_value_int = 1
    else:
        status_value_int = 0

    query = f"""UPDATE users SET {status} = {status_value_int} where telegram_id = %s"""
    args = (user_id, )
    res = mydb_commands.write(db, query, args, return_rowcount=True)

    mydb_commands.close(db)

    if res == 0:
        print(f"User {user_id} is not found in database")
        return False

    print(f"Assigned a status {status} to user {user_id}")

    return True


async def update_use_date(user):
    db = mydb_commands.connect()

    query = """UPDATE users SET last_use_date = now() where telegram_id = %s"""
    args = (user.id,)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"Updating the time of the last usage - User {user.id}", True


def save_user(user):

    db = mydb_commands.connect()

    query = """ INSERT INTO users (telegram_id, name, lang) 
                VALUES (%s, %s, %s) 
                ON DUPLICATE KEY UPDATE telegram_id = VALUES(telegram_id), name = %s, lang = %s"""
    args = (user.id, user.name, user.lang, user.name, user.lang)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"User {user.id} has been saved in database", True


def check_is_ok(args):

    key = args[0]

    db = mydb_commands.connect()
    query = "SELECT Count(*) FROM doms WHERE mykey = %s"
    args = (key,)
    count = mydb_commands.read_one_value(db, query, args)
    logger.info(f"found {count} {key} in doms table")

    query = "SELECT Count(*) FROM access WHERE mykey = %s"
    count2 = mydb_commands.read_one_value(db, query, args)
    logger.info(f"found {count} {key} in access table")

    mydb_commands.close(db)

    if count > 0 or count2 > 0:
        return f"ID {key} already exists in database", False

    return f"Adding key {key} to database", True


def delete_access_key(user, key):

    db = mydb_commands.connect()

    query = """ DELETE from access WHERE telegram_id = %s AND mykey = %s"""
    args = (user.id, key)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"User {user.id} and key {key} pair has been removed from database", True


def add_access_key(user, key):

    db = mydb_commands.connect()

    query = """ INSERT INTO access (telegram_id, mykey) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE telegram_id = VALUES(telegram_id), mykey = VALUES(mykey)"""
    args = (user.id, key)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"User {user.id} and key {key} pair has been added to database", True


def add_house(house_name, key):

    db = mydb_commands.connect()

    query = """ INSERT INTO doms (name, mykey) 
                VALUES (%s, %s) 
                ON DUPLICATE KEY UPDATE name = VALUES(name), mykey = VALUES(mykey)"""
    args = (house_name, key)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"House {house_name} with key {key} has been added to database", True


def add_imagga_use(api_key, response, user_id):

    query = """ INSERT INTO imagga_usage (api_key, response, user_id) 
                    VALUES (%s, %s, %s) 
                    ON DUPLICATE KEY UPDATE api_key = VALUES(api_key), response = VALUES(response), user_id = VALUES(user_id)"""
    args = (
    api_key, response, user_id)

    db = mydb_commands.connect()
    mydb_commands.write(db, query, args)
    mydb_commands.close(db)


def add_item(dom_id, location, name, type, user_id, item_class, item_emoji, has_img=False, tags=None, demo_role=None):

    if tags is None or len(tags) == 0:
        tags_str = None
        tagged_by = None
        tags_date = datetime.datetime(2000, 1, 1)
    else:
        tags_str = json.dumps(tags)
        tagged_by = user_id
        tags_date = datetime.datetime.now()

    query = """ INSERT INTO dom (dom_id, location, name, type, user_id, item_class, item_emoji, has_img, tags, tagged_by, tags_date, demo_role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                ON DUPLICATE KEY UPDATE dom_id = VALUES(dom_id), location = VALUES(location), name = VALUES(name), type = VALUES(type), user_id = VALUES(user_id), item_class = VALUES(item_class), item_emoji = VALUES(item_emoji), has_img = VALUES(has_img), tags = VALUES(tags), tagged_by = VALUES(tagged_by), tags_date = VALUES(tags_date), demo_role = VALUES(demo_role)"""
    args = (dom_id, location, name, type, user_id, item_class, item_emoji, has_img, tags_str, tagged_by, tags_date, demo_role)

    db = mydb_commands.connect()
    last_id = mydb_commands.write(db, query, args)
    mydb_commands.close(db)

    return last_id, "Name {name} with type {type} has been added to house {dom_id}, address: {location}, added by user {user_id}, name id - {last_id}"


async def delete_item(item_id):

    db = mydb_commands.connect()

    query = f"DELETE FROM dom WHERE id = %s "
    args = (item_id,)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"Item id {item_id} deleted", True


def delete_dom_and_key(dom_id):

    mykey = get_dom_access_key(dom_id)

    db = mydb_commands.connect()

    query = f"DELETE FROM doms WHERE id = %s "
    args = (dom_id,)
    mydb_commands.write(db, query, args)

    query = f"DELETE FROM access WHERE mykey = %s "
    args = (mykey,)

    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"House id {dom_id} and its keys deleted", True


async def update_item(table, mykey, attribute, value, where):

    db = mydb_commands.connect()

    query = f"UPDATE {table} SET {attribute} = %s WHERE {mykey} = %s """
    args = (value, where)
    mydb_commands.write(db, query, args)

    mydb_commands.close(db)

    return f"Updated an item with {mykey} {where}, changed attribute {attribute} value to  {value} in table {table}", True
