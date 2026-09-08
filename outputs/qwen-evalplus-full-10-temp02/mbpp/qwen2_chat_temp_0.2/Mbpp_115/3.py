def empty_dit(dict_list):
    """
    Check if all dictionaries in the given list are empty.
    
    Args:
    dict_list (list): A list of dictionaries.
    
    Returns:
    bool: True if all dictionaries are empty, False otherwise.
    """
    # Iterate through each dictionary in the list
    for d in dict_list:
        # Check if the dictionary is not empty
        if d:
            return False
    # If all dictionaries are empty, return True
    return True