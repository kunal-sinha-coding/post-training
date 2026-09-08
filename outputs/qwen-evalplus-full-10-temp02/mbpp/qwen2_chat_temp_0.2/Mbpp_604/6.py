# Define the function to reverse words in a given string
def reverse_words(s):
    # Split the string into words using the space character as a delimiter
    words = s.split()
    # Reverse the list of words
    words.reverse()
    # Join the reversed list of words back into a string with spaces in between
    reversed_string = ' '.join(words)
    return reversed_string
