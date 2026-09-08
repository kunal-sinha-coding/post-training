import re

def text_lowercase_underscore(text):
    # Use regular expression to find sequences of lowercase letters joined with an underscore
    return bool(re.search(r'(?<=\w)_\w+', text))
