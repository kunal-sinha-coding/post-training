import re

def extract_quotation(input_string):
    # Use regular expression to find all occurrences of quotation marks " "
    matches = re.findall(r'"\s*', input_string)
    # Return the list of extracted values
    return matches
