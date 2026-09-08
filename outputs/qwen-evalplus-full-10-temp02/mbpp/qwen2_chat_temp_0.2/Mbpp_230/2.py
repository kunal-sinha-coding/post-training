def replace_blank(input_string, replacement_char):
    """
    This function takes in a string and a character, replaces blank spaces in the string with the character, and returns the string.
    
    Args:
    input_string (str): The string to be modified.
    replacement_char (str): The character to replace blank spaces with.
    
    Returns:
    str: The modified string with blank spaces replaced by the replacement character.
    """
    # Replace all spaces in the input string with the replacement character
    modified_string = input_string.replace(" ", replacement_char)
    return modified_string