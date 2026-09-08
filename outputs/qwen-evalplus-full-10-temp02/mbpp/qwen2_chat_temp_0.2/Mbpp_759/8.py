import re

def is_decimal(s):
    # Regular expression to match a decimal number with a precision of 2
    pattern = r'^-?\d+(\.\d{1,2})?$'
    # Using re.match to check if the string matches the pattern
    if re.match(pattern, s):
        return True
    else:
        return False
