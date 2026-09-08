def text_match_wordz_middle(text):
    """
    Check if a string contains 'z', except at the start and end of the word.
    
    Args:
    text (str): The string to be checked.
    
    Returns:
    bool: True if 'z' is not at the start or end of the word, False otherwise.
    """
    # Check if the string is longer than 2 characters
    if len(text) > 2:
        # Check if 'z' is at the start or end of the string
        if text[0] != 'z' or text[-1] != 'z':
            return True
    return False
