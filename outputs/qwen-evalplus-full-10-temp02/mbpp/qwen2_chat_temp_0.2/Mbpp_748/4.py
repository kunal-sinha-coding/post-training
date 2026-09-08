def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty list to store the result
    result = []
    # Flag to check if the first word is capitalized
    capitalize = True
    # Iterate over each word in the list
    for word in words:
        # If the word is not capitalized, add a space and set the flag to False
        if not capitalize:
            result.append(' ')
            capitalize = True
        # Add the word to the result list
        result.append(word)
    # Join the list into a string with spaces between words
    return ' '.join(result)
