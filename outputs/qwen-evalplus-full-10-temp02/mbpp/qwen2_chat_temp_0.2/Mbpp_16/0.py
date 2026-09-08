def text_lowercase_underscore(text):
    # Split the string into words
    words = text.split('_')
    # Check if any word contains only lowercase letters
    for word in words:
        if all(char.islower() for char in word):
            return True
    return False