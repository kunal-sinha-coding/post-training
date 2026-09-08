def text_lowercase_underscore(text):
    """
    Check if the input string contains sequences of lowercase letters joined with an underscore.
    
    Args:
    text (str): The input string to check.
    
    Returns:
    bool: True if the string contains sequences of lowercase letters joined with an underscore, False otherwise.
    """
    # Split the string by underscores and check if any part is a sequence of lowercase letters
    return any(word.islower() for word in text.split('_'))
