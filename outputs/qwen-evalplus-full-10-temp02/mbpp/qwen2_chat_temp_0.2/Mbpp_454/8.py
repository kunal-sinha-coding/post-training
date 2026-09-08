import re

def text_match_wordz(text):
    # Define the pattern to match a word containing 'z'
    pattern = r'\b\w*z\b'
    # Use re.search to find the pattern in the text
    if re.search(pattern, text):
        return True
    else:
        return False