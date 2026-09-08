def find_substring(string_list, substring):
    """
    Check if a substring is present in a given list of string values.
    
    Parameters:
    string_list (list of str): The list of strings to search within.
    substring (str): The substring to search for.
    
    Returns:
    bool: True if the substring is found in the list, False otherwise.
    """
    for string in string_list:
        if substring in string:
            return True
    return False