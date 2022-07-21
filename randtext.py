import random


def get_rand_char():
    chars = "abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    num = random.randrange(len(chars))
    return chars[num]


def get_random_string(length):
    key = ""
    for i in range(length): key = key + get_rand_char()
    return key
