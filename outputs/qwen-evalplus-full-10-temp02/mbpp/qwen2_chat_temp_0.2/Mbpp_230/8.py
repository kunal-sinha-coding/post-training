def replace_blank(input_string, replacement_char):
    """
    Replace blank spaces in the input_string with the replacement_char and return the modified string.
    
    Parameters:
    input_string (str): The string to be modified.
    replacement_char (str): The character to replace blank spaces with.
    
    Returns:
    str: The modified string with blank spaces replaced by the replacement_char.
    """
    # Replace all spaces in the input_string with the replacement_char
    modified_string = input_string.replace(" ", replacement_char)
    return modified_string
