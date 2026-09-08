def merge_dictionaries_three(dict1, dict2, dict3):
    # Merge the dictionaries using the update method
    merged_dict = dict1.update(dict2).update(dict3)
    return merged_dict