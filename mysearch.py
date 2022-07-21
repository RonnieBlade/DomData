import pylev


def compare(a, b):
    distance = pylev.levenshtein(a.lower(), b.lower())
    return distance
