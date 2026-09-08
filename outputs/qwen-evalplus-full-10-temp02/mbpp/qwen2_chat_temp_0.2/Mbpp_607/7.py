import re

def find_literals(text, pattern):
    """
    Search for a regex pattern in a given text and return the matching subtring, start index, and end index.
    
    Parameters:
    text (str): The text to search within.
    pattern (str): The regex pattern to search for.
    
    Returns:
    tuple: A tuple containing the matched substring, start index, and end index.
    """
    match = re.search(pattern, text)
    if match:
        return match.group(), match.start(), match.end()
    else:
        return None, None, None
