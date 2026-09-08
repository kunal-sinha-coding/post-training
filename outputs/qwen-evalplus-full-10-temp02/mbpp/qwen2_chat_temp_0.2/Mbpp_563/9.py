import re

def extract_values(input_string):
    # Use regular expression to find all occurrences of quotation marks and extract the values
    extracted_values = re.findall(r'"([^"]*)"', input_string)
    return extracted_values
