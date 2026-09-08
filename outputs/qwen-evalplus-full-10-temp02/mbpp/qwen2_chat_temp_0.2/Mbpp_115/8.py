def empty_dit(dict_list):
    # Iterate through each dictionary in the list
    for dictionary in dict_list:
        # Check if the dictionary is empty
        if not dictionary:
            # Return True if all dictionaries are empty
            return True
    # If no dictionaries are empty, return False
    return False