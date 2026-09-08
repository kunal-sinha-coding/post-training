def text_match_two_three(text):
    """
    Check if the input string contains the 'a' character followed by two or three 'b' characters.
    
    Args:
    text (str): The string to be checked.
    
    Returns:
    bool: True if the string contains 'a' followed by two or three 'b', False otherwise.
    """
    # Check if the string contains 'a' followed by two or three 'b'
    return 'ab' in text or 'ba' in text
