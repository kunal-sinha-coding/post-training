def start_withp(words):
    """
    This function takes a list of words and returns two words from the list that start with the letter 'p'.
    
    Args:
    words (list): A list of words.
    
    Returns:
    tuple: A tuple containing two words from the list that start with the letter 'p'.
    """
    # Initialize two variables to store the words that start with 'p'
    word1 = ""
    word2 = ""
    
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with 'p'
        if word.startswith('p'):
            # If it does, update the variables with the current word
            word1 = word
            word2 = word
    
    # Return the two words
    return (word1, word2)
