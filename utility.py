

def add_key(dictionary, key_list, value):

    for key in key_list[:-1]:
        dictionary = dictionary.setdefault(key, {})
    dictionary[key_list[-1]] = value
