import re

def remove_uppercase(input_string):
    # Use regular expression to replace all uppercase letters with an empty string
    result = re.sub('[A-Z]', '', input_string)
    return result
