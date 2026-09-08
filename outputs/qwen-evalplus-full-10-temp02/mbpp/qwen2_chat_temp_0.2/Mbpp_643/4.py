def text_match_wordz_middle(text):
    """
    Check if a string contains 'z', except at the start and end of the word.
    
    Args:
    text (str): The string to check.
    
    Returns:
    bool: True if 'z' is not at the start or end of the word, False otherwise.
    """
    # Check if the string is longer than 2 characters
    if len(text) > 2:
        # Check if the character before the first character is 'z' and the character after the last character is 'z'
        if text[1] != 'z' and text[-2] != 'z':
            return True
    return False
