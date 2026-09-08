def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty list to store the result
    result = []
    # Flag to check if the first word is capitalized
    capitalize = True
    # Iterate over each word in the list
    for word in words:
        # If the word is capitalized, add a space
        if word[0].isupper():
            if capitalize:
                result.append(word)
                capitalize = False
            else:
                result.append(' ' + word)
        else:
            # If the word is not capitalized, add it as is
            result.append(word)
    # Join the list into a string with spaces
    return ' '.join(result)
