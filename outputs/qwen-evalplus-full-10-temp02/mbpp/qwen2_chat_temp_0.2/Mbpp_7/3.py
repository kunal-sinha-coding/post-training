def find_char_long(text):
    """
    This function takes a string as input and returns a set of words that are at least 4 characters long.
    
    Args:
    text (str): The input string to search through.
    
    Returns:
    set: A set of words that are at least 4 characters long.
    """
    # Split the input string into words
    words = text.split()
    # Filter words that are at least 4 characters long
    result = {word for word in words if len(word) >= 4}
    return result