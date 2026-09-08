def find_substring(string_list, substring):
    """
    Check if a string is present as a substring in a given list of string values.
    
    Args:
    string_list (list): A list of strings to search through.
    substring (str): The string to search for within the list.
    
    Returns:
    bool: True if the substring is found in the list, False otherwise.
    """
    # Iterate through each string in the list
    for string in string_list:
        # Check if the current string is equal to the substring
        if string == substring:
            return True
    # If no substring is found, return False
    return False