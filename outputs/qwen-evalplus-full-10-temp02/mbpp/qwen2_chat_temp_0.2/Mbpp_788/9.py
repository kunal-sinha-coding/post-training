def new_tuple(string_list, string):
    """
    Create a new tuple from the given string and list.
    
    Parameters:
    string_list (list): A list of strings.
    string (str): A string to be added to the tuple.
    
    Returns:
    tuple: A tuple containing the original list and the new string.
    """
    # Create a tuple from the list and the string
    new_tuple = tuple(string_list + [string])
    return new_tuple