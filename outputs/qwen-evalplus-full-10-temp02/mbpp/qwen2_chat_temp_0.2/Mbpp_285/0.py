def text_match_two_three(text):
    """
    Check if the given string contains the 'a' character followed by two or three 'b' characters.
    
    Args:
    text (str): The string to be checked.
    
    Returns:
    bool: True if the string contains the required pattern, False otherwise.
    """
    # Check if the string contains the pattern 'ab' or 'ba'
    return 'ab' in text or 'ba' in text
