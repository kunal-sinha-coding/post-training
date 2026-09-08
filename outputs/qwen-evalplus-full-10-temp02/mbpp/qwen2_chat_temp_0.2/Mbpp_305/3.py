def start_withp(words):
    """
    Return two words from a list of words starting with letter 'p'.
    
    Parameters:
    words (list): A list of words.
    
    Returns:
    tuple: A tuple containing two words from the list that start with 'p'.
    """
    # Filter words starting with 'p' and return them
    return tuple(word for word in words if word.startswith('p'))
