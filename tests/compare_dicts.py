from deepdiff import DeepDiff


def compare_dicts(states, dumped_states):
    diff = DeepDiff(states, dumped_states, ignore_order=True, ignore_numeric_type_changes=True)
    if "dictionary_item_added" in diff:
        del diff["dictionary_item_added"]
    if diff != {}:
        diff = recur_remove_added_items(diff)
    if diff != {}:
        if "values_changed" in diff:
            for key, value in diff["values_changed"].items():
                diff_ = DeepDiff(value["new_value"], value["old_value"], ignore_order=True, ignore_numeric_type_changes=True)
                print(f"Difference in key {key}: {diff_}")
    return diff

def recur_remove_added_items(diff):
    if "dictionary_item_added" in diff:
        del diff["dictionary_item_added"]
    else:
        return diff
    if "values_changed" in diff:
        for key, value in diff["values_changed"].items():
            diff_ = DeepDiff(value["new_value"], value["old_value"], ignore_order=True, ignore_numeric_type_changes=True)
            recur_remove_added_items(diff_)