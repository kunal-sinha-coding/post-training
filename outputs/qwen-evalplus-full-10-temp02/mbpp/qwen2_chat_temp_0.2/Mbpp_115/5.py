def empty_dit(dict_list):
    # Check if all dictionaries in the list are empty
    return all(not d for d in dict_list)