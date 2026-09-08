def long_words(n, words):
    # Initialize an empty list to store words longer than n characters
    result = []
    # Iterate through each word in the input list
    for word in words:
        # Check if the length of the word is greater than n
        if len(word) > n:
            # If true, append the word to the result list
            result.append(word)
    # Return the list of words that are longer than n characters
    return result