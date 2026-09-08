def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty list to store the result
    result = []
    # Iterate over each word in the list
    for word in words:
        # Check if the word starts with a capital letter
        if word[0].isupper():
            # Add the word to the result list with a space
            result.append(word + ' ')
        else:
            # If the word does not start with a capital letter, add it as is
            result.append(word)
    # Join the result list into a single string with spaces
    return ' '.join(result)
