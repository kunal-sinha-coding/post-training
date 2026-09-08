def empty_dit(list_of_dicts):
    # Check if all dictionaries in the list are empty
    return all(not dict_ for dict_ in list_of_dicts)