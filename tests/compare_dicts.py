from deepdiff import DeepDiff


def compare_dicts(default, changed, max_depth = 10):
    """
    Compares two dictionaries, returning a dictionary of differences
    :param default: The default dictionary
    :param changed: The dictionary to compare to the default
    :param max_depth: The maximum depth to compare to
    """
    a =  recur_compare_keys(default, changed, 0, "", max_depth)
    b = recur_compare_values(default, changed, 0, "", max_depth)

    return a and b

def recur_compare_keys(dict1, dict2, depth, path, max_depth):
    good = True
    if depth >= max_depth:
        return True
    if "@c" in dict1:
        path += dict1["@c"] + "->"

    for key in dict1.keys():
        if key not in dict2:
            print(f"Key {key} at path {path} not found in changed")
            good =  False
        else:
            if isinstance(dict1[key], dict):
                good = good and recur_compare_keys(dict1[key], dict2[key], depth + 1, path + f": {key} ", max_depth)
            elif isinstance(dict1[key], list):
                good = good and recur_list_key_compare(dict1[key], dict2[key], depth + 1, path  + f": {key} ", max_depth)


    return good

def recur_list_key_compare(list1, list2, depth, path, max_depth):
    good = True
    if depth >= max_depth:
        return True

    list1 = sorted(list1, key = custom_list_sort)
    list2 = sorted(list2, key = custom_list_sort)

    for i in range(len(list1)):
        if isinstance(list1[i], dict):
            path += "index: " + str(i) + ""
            good = good and recur_compare_keys(list1[i], list2[i], depth + 1, path + f": {str(list1[i])[:10]} ->", max_depth)
        elif isinstance(list1[i], list):
            path += "index: " + str(i) + ""
            good = good and recur_list_key_compare(list1[i], list2[i], depth + 1, path + f": {str(list1[i])[:10]} ->", max_depth)
        else:
            if list1[i] != list2[i]:
                print(f"Value at path {path} is different: \n {str(list1[i])[:1000]} \n {str(list2[i])[:1000]}")
                good = False

    return good

def recur_compare_values(dict1, dict2, depth, path, max_depth):
    if depth >= max_depth:
        return True
    if "@c" in dict1:
        path += dict1["@c"] + "->"

    good = True
    for key in dict1.keys():
        if isinstance(dict1[key], dict):
            good = good and recur_compare_values(dict1[key], dict2[key], depth + 1, path + f": {key}", max_depth)
        elif isinstance(dict1[key], list):
            good = good and recur_list_value_compare(dict1[key], dict2[key], depth + 1, path  + f": {key} ", max_depth)
        else:
            if dict1[key] != dict2[key]:

                print(f"Value at path {path+str(key)} is different: \n {str(dict1[key])[:1000]} \n {str(dict2[key])[:1000]}")
                good = False

    return good

def custom_list_sort(item):
    if isinstance(item, dict):
        if 'id' in item:
            return (0, item['id'])
        elif '@c' in item:
            return (0, item['@c'])
        elif 'timeStamp' in item:
            return (0, item['timeStamp'])
        else:
            return (0, len(item))
    elif isinstance(item, list):
        return (1, len(item))
    else:
        return (2, item)

def recur_list_value_compare(list1, list2, depth, path, max_depth):
    if depth >= max_depth:
        return True

    good = True

    # sort both lists. dicts first then lists then values. dicts are sorted by their id key if it exists. check if for id if is dict
    list1 = sorted(list1, key = custom_list_sort)
    list2 = sorted(list2, key = custom_list_sort)

    for i in range(len(list1)):
        if isinstance(list1[i], dict):
            path += "index: " + str(i) + ""
            good = good and recur_compare_values(list1[i], list2[i], depth + 1, path + f": {str(list1[i])[:10]} ->", max_depth)
        elif isinstance(list1[i], list):
            path += "index: " + str(i) + ""
            good = good and recur_list_value_compare(list1[i], list2[i], depth + 1, path + f": {str(list1[i])[:10]} ->", max_depth)
        else:
            if list1[i] != list2[i]:
                print(f"Value at path {path} is different: \n {str(list1[i])[:1000]} \n {str(list2[i])[:1000]}")
                good = False

    return good


def deepdiff(original, changed):
    diff = DeepDiff(original, changed, ignore_order=True, ignore_numeric_type_changes=True)
    if "dictionary_item_added" in diff:
        del diff["dictionary_item_added"]
    if diff != {}:
        if "values_changed" in diff:
            for key, value in diff["values_changed"].items():
                diff_ = DeepDiff(value["old_value"],value["new_value"], ignore_order=True, ignore_numeric_type_changes=True)
                print(f"Difference in key {key}: {diff_}")
    return diff