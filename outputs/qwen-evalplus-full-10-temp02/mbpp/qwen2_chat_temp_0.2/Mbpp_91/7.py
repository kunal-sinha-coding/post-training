def find_substring(string_list, substring):
    """
    Check if a string is present as a substring in a given list of string values.
    
    Args:
    string_list (list of str): The list of string values to search through.
    substring (str): The string to search for within the list.
    
    Returns:
    bool: True if the substring is found in the list, False otherwise.
    """
    for string in string_list:
        if string == substring:
            return True
    return False
