def find_char_long(s):
    """
    This function takes a string as input and returns a set of words that are at least 4 characters long.
    
    Args:
    s (str): The input string to search through.
    
    Returns:
    set: A set of words that are at least 4 characters long.
    """
    # Split the string into words
    words = s.split()
    # Filter words that are at least 4 characters long
    filtered_words = [word for word in words if len(word) >= 4]
    return filtered_words