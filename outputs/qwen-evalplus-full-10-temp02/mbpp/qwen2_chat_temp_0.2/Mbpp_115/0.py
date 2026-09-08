def empty_dit(dict_list):
    # Check if all dictionaries in the list are empty
    for dictionary in dict_list:
        if not dictionary:
            return True
    # If all dictionaries are empty, return False
    return False