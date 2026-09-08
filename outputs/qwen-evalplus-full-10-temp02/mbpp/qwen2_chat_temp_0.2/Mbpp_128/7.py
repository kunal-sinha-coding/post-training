def long_words(n, words):
    # Initialize an empty list to store words longer than n characters
    long_words = []
    # Iterate through each word in the input list
    for word in words:
        # Check if the length of the word is greater than n
        if len(word) > n:
            # Append the word to the long_words list
            long_words.append(word)
    # Return the list of words that are longer than n characters
    return long_words