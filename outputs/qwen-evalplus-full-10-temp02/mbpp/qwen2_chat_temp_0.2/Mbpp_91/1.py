def find_substring(string_list, substring):
    """
    Check if a substring is present in a given list of string values.

    Args:
    string_list (list): A list of strings to search through.
    substring (str): The substring to search for.

    Returns:
    bool: True if the substring is found in the list, False otherwise.
    """
    # Iterate through each string in the list
    for string in string_list:
        # Check if the current string is equal to the substring
        if string == substring:
            return True
    # If the loop completes without finding the substring, return False
    return False