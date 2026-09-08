import re

def extract_quotation(text):
    # Use regular expression to find all occurrences of quotation marks " "
    return re.findall(r'"\s+"', text)
