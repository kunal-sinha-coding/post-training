def text_starta_endb(text):
    """
    This function checks if the input string starts with 'a' and ends with 'b'.
    
    Args:
    text (str): The string to be checked.
    
    Returns:
    bool: True if the string starts with 'a' and ends with 'b', False otherwise.
    """
    # Check if the string starts with 'a' and ends with 'b'
    return text.startswith('a') and text.endswith('b')