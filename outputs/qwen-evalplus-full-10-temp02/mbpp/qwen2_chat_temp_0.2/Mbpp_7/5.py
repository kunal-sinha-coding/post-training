def find_char_long(text):
    """
    Find all words in the given text that are at least 4 characters long.
    
    Args:
    text (str): The input string to search through.
    
    Returns:
    set: A set of words that are at least 4 characters long.
    """
    # Split the text into words
    words = text.split()
    # Filter words that are at least 4 characters long
    long_words = [word for word in words if len(word) >= 4]
    return long_words
