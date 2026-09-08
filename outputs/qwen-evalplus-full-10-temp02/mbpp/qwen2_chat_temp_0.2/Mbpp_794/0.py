import re

def text_starta_endb(text):
    # Use regular expression to find the pattern 'a followed by anything, ending in b'
    pattern = r'\b[a]\w*\b'
    # Search for the pattern in the text
    if re.search(pattern, text):
        return True
    else:
        return False
