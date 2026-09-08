def text_lowercase_underscore(text):
    """
    Check if the input string contains sequences of lowercase letters joined with an underscore.
    
    Args:
    text (str): The input string to check.
    
    Returns:
    bool: True if the string contains sequences of lowercase letters joined with an underscore, False otherwise.
    """
    # Split the string into words
    words = text.split()
    
    # Iterate through each word
    for word in words:
        # Check if the word contains lowercase letters
        if any(char.islower() for char in word):
            return True
    
    # If no lowercase letters are found, return False
    return False