def reverse_words(s):
    # Split the string into words using space as the delimiter
    words = s.split()
    # Reverse the list of words
    words.reverse()
    # Join the reversed list of words back into a string with spaces
    return ' '.join(words)