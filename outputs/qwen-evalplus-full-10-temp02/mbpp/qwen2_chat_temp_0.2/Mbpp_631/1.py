def replace_spaces(text):
    """
    Replace whitespaces in the given string with an underscore and vice versa.
    
    Args:
    text (str): The input string to be modified.
    
    Returns:
    str: The modified string with spaces replaced.
    """
    # Replace all spaces with underscores
    modified_text = text.replace(' ', '_')
    # Replace all underscores with spaces
    modified_text = modified_text.replace('_', ' ')
    return modified_text
