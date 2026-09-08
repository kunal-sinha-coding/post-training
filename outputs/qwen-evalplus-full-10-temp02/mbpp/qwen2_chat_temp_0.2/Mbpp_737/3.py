import re

def check_str(s):
    # Define a regular expression pattern to match strings starting with a vowel
    pattern = r'^[aeiouAEIOU]'
    # Use re.match to check if the string matches the pattern
    if re.match(pattern, s):
        return True
    else:
        return False
