import re

def text_lowercase_underscore(text):
    # Use regular expression to find sequences of lowercase letters joined with an underscore
    if re.search(r'(?<=\w)_\w+', text):
        return True
    else:
        return False