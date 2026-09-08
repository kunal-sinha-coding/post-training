# Define the function to find words longer than n characters
def long_words(n, words):
    # Use list comprehension to filter words longer than n characters
    long_words = [word for word in words if len(word) > n]
    return long_words
