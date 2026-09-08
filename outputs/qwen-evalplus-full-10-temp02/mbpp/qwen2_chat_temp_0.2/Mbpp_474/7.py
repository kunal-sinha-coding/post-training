def replace_char(input_string, old_char, new_char):
    """
    Replace all occurrences of old_char with new_char in the input_string.
    
    Parameters:
    input_string (str): The string in which characters will be replaced.
    old_char (str): The character to be replaced.
    new_char (str): The character to replace with.
    
    Returns:
    str: The modified string with all occurrences of old_char replaced by new_char.
    """
    # Using the replace() method to replace all occurrences of old_char with new_char
    modified_string = input_string.replace(old_char, new_char)
    return modified_string
