# Importing the necessary module
from typing import List

def reverse_words(s: str) -> str:
    # Splitting the string into words using space as the delimiter
    words = s.split()
    # Reversing the list of words
    words.reverse()
    # Joining the reversed list of words back into a string with spaces
    reversed_string = ' '.join(words)
    return reversed_string
