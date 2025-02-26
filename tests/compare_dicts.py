def dict_contains(original, modified, path="root"):
    """
    Check if modified contains all the data from original.
    """
    if isinstance(original, dict):
        if not isinstance(modified, dict):
            return False, f"PATH: {path} | ERROR: Expected dict, found {type(modified).__name__}"

        for key, value in original.items():
            current_path = f"{path}.{key}"
            if key not in modified:
                # Convert keys to strings before joining
                available_keys = [str(k) for k in list(modified.keys())[:5]]
                return False, f"PATH: {current_path} | ERROR: Missing key '{key}' | AVAILABLE KEYS: {', '.join(available_keys)}"

            contains, debug_info = dict_contains(value, modified[key], current_path)
            if not contains:
                return False, debug_info
        return True, None

    elif isinstance(original, list):
        if not isinstance(modified, list):
            return False, f"PATH: {path} | ERROR: Expected list, found {type(modified).__name__}"

        if len(original) > len(modified):
            return False, f"PATH: {path} | ERROR: Original list has {len(original)} items, modified has only {len(modified)}"

        for i, orig_item in enumerate(original):
            found = False
            all_errors = []

            for j, mod_item in enumerate(modified):
                contains, debug_info = dict_contains(orig_item, mod_item, f"{path}[{i}]")
                if contains:
                    found = True
                    break
                all_errors.append(debug_info)

            if not found:
                return False, f"PATH: {path}[{i}] | ERROR: No matching item found | FIRST COMPARE ERROR: {all_errors[0] if all_errors else 'Unknown'}"
        return True, None

    # For primitive values
    if original != modified:
        return False, f"PATH: {path} | ERROR: Value mismatch | EXPECTED: {original} ({type(original).__name__}) | FOUND: {modified} ({type(modified).__name__})"
    return True, None


# Fix your helper function to always raise when testing
def test_dict_contains(original, modified, expect_failure=False):
    contains, debug_info = dict_contains(original, modified)
    if expect_failure:
        if contains:
            raise AssertionError("Expected data mismatch but dictionaries matched")
        else:
            raise AssertionError(debug_info)
    elif not contains:
        raise AssertionError(debug_info)
    return True