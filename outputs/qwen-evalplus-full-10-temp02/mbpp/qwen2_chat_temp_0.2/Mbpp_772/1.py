import re
def remove_length(text, k):
    # Use regular expression to find all words with length k
    result = re.findall(r'\b\w{1,}k\b', text)
    # Join the found words into a single string and return
    return ' '.join(result)