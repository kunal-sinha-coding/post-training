import re

def extract_quotation(input_string):
    # Use regular expression to find all occurrences of quotation marks " "
    # and return them as a list
    return re.findall(r'"\w+"', input_string)
