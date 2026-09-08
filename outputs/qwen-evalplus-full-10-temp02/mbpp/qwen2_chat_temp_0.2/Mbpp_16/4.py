def text_lowercase_underscore(text):
    """
    This function checks if the input string contains sequences of lowercase letters joined with an underscore.
    
    Args:
    text (str): The input string to check.
    
    Returns:
    bool: True if the string contains sequences of lowercase letters joined with an underscore, False otherwise.
    """
    # Split the string into words
    words = text.split('_')
    # Check if any word contains only lowercase letters
    for word in words:
        if all(char.islower() for char in word):
            return True
    return False