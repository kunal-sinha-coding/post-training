def capital_words_spaces(text):
    """
    This function takes a string and returns a new string where each word starting with a capital letter is separated by a space.
    
    Args:
    text (str): The input string to be processed.
    
    Returns:
    str: A new string with spaces between words starting with capital letters.
    """
    # Split the input string into words
    words = text.split()
    # Initialize an empty list to store words with capital letters
    result = []
    # Iterate over each word in the list
    for word in words:
        # Check if the word starts with a capital letter
        if word[0].isupper():
            # Append the word to the result list with a space
            result.append(word + ' ')
        else:
            # If the word does not start with a capital letter, add it to the result list as is
            result.append(word)
    # Join the words in the result list into a single string with spaces
    return ' '.join(result)
