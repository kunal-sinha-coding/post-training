def merge_dictionaries_three(dict1, dict2, dict3):
    # Create a new dictionary that is a combination of the input dictionaries
    merged_dict = {**dict1, **dict2, **dict3}
    return merged_dict