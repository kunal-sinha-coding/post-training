import re

def replace_spaces(text):
    """
    Replace whitespaces in the given string with an underscore and vice versa.
    
    Args:
    text (str): The input string to be modified.
    
    Returns:
    str: The modified string with spaces replaced.
    """
    # Replace all spaces with underscores
    modified_text = re.sub(r' ', '_', text)
    # Replace all underscores with spaces
    modified_text = re.sub(r'_', ' ', modified_text)
    return modified_text
