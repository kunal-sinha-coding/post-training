import re

def find_literals(text, pattern):
    # Use re.search to find the pattern in the text
    match = re.search(pattern, text)
    # If a match is found, return the matched substring, start index, and end index
    if match:
        return match.group(), match.start(), match.end()
    else:
        # Return None if no match is found
        return None
