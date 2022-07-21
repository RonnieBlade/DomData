# number system converter python

ALPHABET = \
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode(n):
    try:
        return ALPHABET[n]
    except IndexError:
        raise Exception("cannot encode: %s" % n)


def dec_to_base(dec=0, base=62):
    if dec < base:
        return encode(dec)
    else:
        return dec_to_base(dec // base, base) + encode(dec % base)


