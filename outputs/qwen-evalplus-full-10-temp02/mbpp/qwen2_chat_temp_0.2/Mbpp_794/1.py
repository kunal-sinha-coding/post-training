import re

def text_starta_endb(text):
    # Use regular expression to find the pattern 'a followed by anything, ending in b'
    match = re.search(r'a.*b$', text)
    # Return True if a match is found, otherwise False
    return bool(match)
