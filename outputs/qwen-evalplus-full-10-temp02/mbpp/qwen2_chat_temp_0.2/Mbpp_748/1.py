def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty list to store the result
    result = []
    # Iterate over each word
    for word in words:
        # Check if the word starts with a capital letter
        if word[0].isupper():
            # Add a space before the word
            result.append(' ' + word)
        else:
            # Add the word as is
            result.append(word)
    # Join the list into a string with spaces
    return ' '.join(result)
