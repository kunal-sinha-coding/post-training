def replace_char(str1, old_char, new_char):
    """
    Replace all occurrences of old_char with new_char in the string str1.
    
    Parameters:
    str1 (str): The original string.
    old_char (str): The character to be replaced.
    new_char (str): The character to replace with.
    
    Returns:
    str: The modified string with all occurrences of old_char replaced by new_char.
    """
    # Replace all occurrences of old_char with new_char in the string
    modified_str = str1.replace(old_char, new_char)
    return modified_str
