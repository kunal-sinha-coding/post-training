import re

def remove_uppercase(input_string):
    # Use regular expression to remove all uppercase letters
    result = re.sub('[A-Z]', '', input_string)
    return result
