import re

def text_match_wordz(text):
    # Define the pattern to match a word containing 'z'
    pattern = r'\b\w*z\w*\b'
    # Search for the pattern in the given text
    if re.search(pattern, text):
        return True
    else:
        return False