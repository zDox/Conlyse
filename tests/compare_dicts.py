from deepdiff import DeepDiff


def compare_dicts(default, changed, max_depth=10):
    """
    Compares two dictionaries, returning True if they match within constraints
    :param default: The default dictionary
    :param changed: The dictionary to compare to the default
    :param max_depth: The maximum depth to compare to
    :return: True if dictionaries match within constraints, False otherwise
    """
    key_comparison = recur_compare_keys(default, changed, 0, "", max_depth)
    value_comparison = recur_compare_values(default, changed, 0, "", max_depth)

    return key_comparison and value_comparison


def recur_compare_keys(dict1, dict2, depth, path, max_depth):
    """
    Recursively compares keys between two dictionaries
    """
    good = True
    if depth >= max_depth:
        return True

    current_path = path
    if "@c" in dict1:
        current_path = path + dict1["@c"] + "/"

    for key in dict1.keys():
        key_path = f"{current_path}{key}"

        if key not in dict2:
            print(f"Key '{key}' not found in changed dictionary at path: {current_path}")
            good = False
        else:
            if isinstance(dict1[key], dict):
                good = good and recur_compare_keys(dict1[key], dict2[key], depth + 1, f"{current_path}{key}/",
                                                   max_depth)
            elif isinstance(dict1[key], list):
                good = good and recur_list_key_compare(dict1[key], dict2[key], depth + 1, f"{current_path}{key}/",
                                                       max_depth)

    return good


def recur_list_key_compare(list1, list2, depth, path, max_depth):
    """
    Recursively compares keys in list elements
    """
    good = True
    if depth >= max_depth:
        return True

    # Sort both lists for comparison
    list1 = sorted(list1, key=custom_list_sort)
    list2 = sorted(list2, key=custom_list_sort)

    # Check if lists have same length
    if len(list1) != len(list2):
        print(f"Lists at path {path} have different lengths: {len(list1)} vs {len(list2)}")
        return False

    for i in range(len(list1)):
        item_path = f"{path}[{i}]/"

        if isinstance(list1[i], dict):
            good = good and recur_compare_keys(list1[i], list2[i], depth + 1, item_path, max_depth)
        elif isinstance(list1[i], list):
            good = good and recur_list_key_compare(list1[i], list2[i], depth + 1, item_path, max_depth)
        else:
            if list1[i] != list2[i]:
                print(f"Value at path {item_path} is different:")
                print(f"  Original ({type(list1[i]).__name__}): {str(list1[i])[:1000]}")
                print(f"  Processed ({type(list2[i]).__name__}): {str(list2[i])[:1000]}")
                good = False

    return good


def recur_compare_values(dict1, dict2, depth, path, max_depth):
    """
    Recursively compares values between two dictionaries
    """
    if depth >= max_depth:
        return True

    current_path = path
    if "@c" in dict1:
        current_path = path + dict1["@c"] + "/"

    good = True
    for key in dict1.keys():
        key_path = f"{current_path}{key}"

        if isinstance(dict1[key], dict):
            good = good and recur_compare_values(dict1[key], dict2[key], depth + 1, f"{current_path}{key}/", max_depth)
        elif isinstance(dict1[key], list):
            good = good and recur_list_value_compare(dict1[key], dict2[key], depth + 1, f"{current_path}{key}/",
                                                     max_depth)
        else:
            if dict1[key] != dict2[key]:
                print(f"Value at path {key_path} is different:")
                print(f"  Original ({type(dict1[key]).__name__}): {str(dict1[key])[:1000]}")
                print(f"  Processed ({type(dict2[key]).__name__}): {str(dict2[key])[:1000]}")
                good = False
            elif type(dict1[key]) != type(dict2[key]):
                # Allow int to float conversion (most floats with no decimal places are interpreted as ints)
                if type(dict1[key]) is int and type(dict2[key]) is float:
                    continue
                print(f"Type at path {key_path} is different:")
                print(f"  Original: {type(dict1[key]).__name__}")
                print(f"  Processed: {type(dict2[key]).__name__}")
                good = False

    return good


def custom_list_sort(item):
    """
    Custom sorting function for list elements
    """
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
    """
    Recursively compares values in list elements
    """
    if depth >= max_depth:
        return True

    good = True

    # Check if lists have same length
    if len(list1) != len(list2):
        print(f"Lists at path {path} have different lengths: {len(list1)} vs {len(list2)}")
        return False

    # Sort both lists for comparison
    list1 = sorted(list1, key=custom_list_sort)
    list2 = sorted(list2, key=custom_list_sort)

    for i in range(len(list1)):
        item_path = f"{path}[{i}]/"

        if isinstance(list1[i], dict):
            good = good and recur_compare_values(list1[i], list2[i], depth + 1, item_path, max_depth)
        elif isinstance(list1[i], list):
            good = good and recur_list_value_compare(list1[i], list2[i], depth + 1, item_path, max_depth)
        else:
            if list1[i] != list2[i]:
                print(f"Value at path {item_path} is different:")
                print(f"  Original ({type(list1[i]).__name__}): {str(list1[i])[:1000]}")
                print(f"  Processed ({type(list2[i]).__name__}): {str(list2[i])[:1000]}")
                good = False
            elif type(list1[i]) != type(list2[i]):
                # Allow int to float conversion (most floats with no decimal places are interpreted as ints)
                if type(list1[i]) is int and type(list2[i]) is float:
                    continue
                print(f"Type at path {item_path} is different:")
                print(f"  Original: {type(list1[i]).__name__}")
                print(f"  Processed: {type(list2[i]).__name__}")
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