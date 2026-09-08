import re

def extract_values(s):
    # Use regular expression to find all occurrences of quoted strings
    return re.findall(r'"([^"]*)"', s)
