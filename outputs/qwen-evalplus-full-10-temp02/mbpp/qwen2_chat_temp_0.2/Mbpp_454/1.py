import re

def text_match_wordz(text):
    # Use regular expression to find the word containing 'z'
    if re.search(r'\b\w*z\b', text):
        return True
    else:
        return False