def replace_blank(input_string, replacement_character):
    """
    Replaces blank spaces in the input_string with the replacement_character and returns the modified string.
    
    Parameters:
    input_string (str): The string to be modified.
    replacement_character (str): The character to replace blank spaces with.
    
    Returns:
    str: The modified string with blank spaces replaced by the replacement character.
    """
    # Replace all spaces in the input_string with the replacement_character
    modified_string = input_string.replace(" ", replacement_character)
    return modified_string