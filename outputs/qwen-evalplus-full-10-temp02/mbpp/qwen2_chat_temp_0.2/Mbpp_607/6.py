import re

def find_literals(text, pattern):
    # Use re.search to find the pattern in the text
    match = re.search(pattern, text)
    # Return the matched substring, start index, and end index
    return match.group(), match.start(), match.end()
