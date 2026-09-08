def text_match_wordz_middle(text):
    """
    Check if a string contains 'z', except at the start and end of the word.
    
    Args:
    text (str): The string to be checked.
    
    Returns:
    bool: True if 'z' is not at the start or end of the word, False otherwise.
    """
    # Check if the string is not empty and starts and ends with 'z'
    if text and text.startswith('z') and text.endswith('z'):
        return False
    else:
        return True