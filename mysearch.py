import pylev
import copy


def compare(a, b):
    distance = pylev.levenshtein(a.lower(), b.lower())
    return distance


def replace_multiply_strings_to_one(s, new_c=None, c_array=None):
    if c_array is None:
        c_array = [",", ".", ";", ":", "(", ")", "-", "+", "[", "]", "}", "{"]
    if new_c is None:
        new_c = ""
    for c in c_array:
        s = s.replace(c, new_c)
    return s


def sort_results_by_words_and_full_distance(all_results, query, max_total_dist=50):
    for one_r in all_results:
        all_name_dist = compare(one_r['item'].name, query)
        if one_r['min_dist'] <= 0:
            all_name_dist = all_name_dist / 6
        if 0 < one_r['min_dist'] <= 1:
            all_name_dist = all_name_dist / 3
        if len(one_r['item'].name.split()) == 1 and one_r['min_dist'] > 1:
            all_name_dist = all_name_dist * 4
        one_r.update({'all_name_dist': all_name_dist})
        one_r.update({'total_dist': one_r['min_dist'] + one_r['all_name_dist'] / 2 + one_r['close_words_factor'] * 2})

    max_dist_from_length = len(query) / 3
    if max_dist_from_length < 2:
        max_dist_from_length = 2

    all_results = list(
        filter(lambda r: r['total_dist'] < max_total_dist or r['min_dist'] < max_dist_from_length, all_results))

    return sorted(all_results, key=lambda r: r['total_dist'], reverse=False)


def search_item_by_part_of_name(query, my_things, distance_limit, top_level_only=False, things_only=False):
    query = query.lower()
    query = replace_multiply_strings_to_one(query)
    query = query.replace('ё', "е")

    found_results_list = []

    for thing in my_things:

        s_inf = {'close_words_factor': 0}
        min_dist = 100

        for qw in query.split():
            th_name = thing.name
            th_name = th_name.lower()
            th_name = replace_multiply_strings_to_one(th_name)
            th_name = th_name.replace('ё', "е")
            for word in th_name.split():
                if len(qw) > len(word):
                    long_word_len = len(qw)
                else:
                    long_word_len = len(word)
                dist = compare(word, qw)
                if dist < distance_limit and (dist / long_word_len * 5) < min_dist:
                    min_dist = dist / long_word_len * 5
                if dist == 0:
                    v = 4 - len(word)
                    if v < min_dist:
                        s_inf['close_words_factor'] = s_inf['close_words_factor'] + v
                        min_dist = v

        if min_dist <= distance_limit:
            if not (thing.item_class in {'dom', 'house', 'level', 'room', 'cupboard', 'storage',
                                         'box'} and things_only):
                s_inf.update({'item': thing, 'min_dist': min_dist})
                found_results_list.append(s_inf)

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_part_of_name(query, thing.space, distance_limit)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list


def search_item_by_photo(stags, my_things, max_dist=100, top_level_only=False):
    found_results_list = []

    for thing in my_things:

        if thing.tags is not None and len(thing.tags) != 0 and thing.type not in {"house", "dom", "level", "room"}:
            dist = find_tags_distance(stags, thing.tags)
            if dist is not None and dist < max_dist:
                found_results_list.append({'item': thing, 'min_dist': dist})

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_photo(stags, thing.space, max_dist)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list


def find_tags_distance(tags1_i, tags2_i):
    if tags1_i is None or tags2_i is None:
        return None

    tags1 = copy.deepcopy(tags1_i)
    tags2 = copy.deepcopy(tags2_i)

    if len(tags1) > len(tags2):
        tags1 = tags1[:len(tags2)]
    if len(tags2) > len(tags1):
        tags2 = tags2[:len(tags1)]

    dist = 0
    all_tags = set()

    for t1 in tags1:
        all_tags.add(t1.get("tag"))

    for t2 in tags2:
        all_tags.add(t2.get("tag"))

    for k in all_tags:
        a1 = next((x for x in tags1 if x["tag"] == k), None)
        a2 = next((x for x in tags2 if x["tag"] == k), None)
        if a1 is None:
            dist += a2["c"]
        elif a2 is None:
            dist += a1["c"]
        elif a1 is not None and a2 is not None:
            dist += abs(a1["c"] - a2["c"])
        else:
            print("No way:)")

    return dist


def search_item_by_class_or_emoji(query, my_things, by_emoji=False, top_level_only=False):
    found_results_list = []

    for thing in my_things:
        if by_emoji:
            value = thing.item_emoji
        else:
            value = thing.item_class

        if value == query:
            found_results_list.append({'item': thing, 'min_dist': 0})

        if len(thing.space) != 0 and not top_level_only:
            found_things_inside = search_item_by_class_or_emoji(query, thing.space, by_emoji)
            if len(found_things_inside) > 0:
                found_results_list.extend(found_things_inside)

    return found_results_list
