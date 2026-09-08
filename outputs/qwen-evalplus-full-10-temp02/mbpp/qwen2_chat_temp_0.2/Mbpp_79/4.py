def word_len(word):
    """
    Check whether the length of the word is odd or not.
    
    Args:
    word (str): The word to check.
    
    Returns:
    bool: True if the length of the word is odd, False otherwise.
    """
    # Check if the length of the word is odd
    return len(word) % 2 != 0