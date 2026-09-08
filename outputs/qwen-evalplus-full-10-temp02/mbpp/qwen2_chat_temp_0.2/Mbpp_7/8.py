def find_char_long(text):
    # Split the text into words
    words = text.split()
    # Initialize an empty set to store words that are at least 4 characters long
    result = set()
    # Iterate over each word in the list
    for word in words:
        # Check if the length of the word is at least 4
        if len(word) >= 4:
            # Add the word to the result set
            result.add(word)
    # Return the result set containing words that are at least 4 characters long
    return result