def replace_blank(input_string, replacement_char):
    """
    Replaces blank spaces in the input_string with the replacement_char.
    
    Parameters:
    input_string (str): The string to be modified.
    replacement_char (str): The character to replace blank spaces with.
    
    Returns:
    str: The modified string with blank spaces replaced.
    """
    # Replace all spaces in the input_string with the replacement_char
    modified_string = input_string.replace(" ", replacement_char)
    return modified_string