def capital_words_spaces(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty string to store the result
    result = ""
    # Iterate over each word in the list
    for word in words:
        # Check if the word starts with a capital letter
        if word[0].isupper():
            # Add a space before the word
            result += " " + word
        else:
            # If the word does not start with a capital letter, add it as is
            result += word
    # Return the result string
    return result
