def new_tuple(string_list, string):
    """
    Create a new tuple from the given string and list.
    
    Parameters:
    string_list (list): A list of strings.
    string (str): A string to be added to the tuple.
    
    Returns:
    tuple: A new tuple containing the original list and the new string.
    """
    # Create a new tuple by concatenating the original list and the new string
    new_tuple = tuple(string_list + [string])
    return new_tuple