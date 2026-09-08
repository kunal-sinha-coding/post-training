def text_lowercase_underscore(text):
    # Split the input string by underscores
    words = text.split('_')
    # Check if the number of words is 1
    if len(words) == 1:
        # Return True if the word is all lowercase
        return words[0].islower()
    else:
        # Return False if the word is not all lowercase
        return False