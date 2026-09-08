def find_substring(string_list, substring):
    """
    Check if a string is present as a substring in a given list of string values.
    
    Parameters:
    string_list (list of str): The list of string values to search within.
    substring (str): The string to search for within each string in the list.
    
    Returns:
    bool: True if the substring is found in any string in the list, False otherwise.
    """
    for string in string_list:
        if substring in string:
            return True
    return False
