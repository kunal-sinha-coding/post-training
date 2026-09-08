def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty list to store the result
    result = []
    # Flag to check if the first word is capitalized
    capitalize = True
    # Iterate through each word in the list
    for word in words:
        # Check if the word starts with a capital letter
        if word[0].isupper():
            # If it is, add a space and capitalize the next letter
            result.append(word + ' ')
            capitalize = False
        else:
            # If it's not, add the word as is
            result.append(word)
    # Join the list into a string with spaces
    return ' '.join(result)
