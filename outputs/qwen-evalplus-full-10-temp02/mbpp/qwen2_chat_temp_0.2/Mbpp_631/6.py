import re

def replace_spaces(s):
    """
    Replace whitespaces in the given string with an underscore and vice versa.
    
    Args:
    s (str): The input string to be modified.
    
    Returns:
    str: The modified string with spaces replaced.
    """
    # Replace all spaces with underscores
    modified_string = re.sub(r' ', '_', s)
    # Replace all underscores with spaces
    modified_string = re.sub(r'_', ' ', modified_string)
    return modified_string
