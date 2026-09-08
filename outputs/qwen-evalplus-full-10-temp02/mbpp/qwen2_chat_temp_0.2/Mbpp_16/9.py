import re

def text_lowercase_underscore(text):
    """
    Check if the input string contains sequences of lowercase letters joined with an underscore.
    
    Args:
    text (str): The input string to check.
    
    Returns:
    bool: True if the string contains sequences of lowercase letters joined with an underscore, False otherwise.
    """
    # Use regular expression to find sequences of lowercase letters joined with an underscore
    if re.search(r'_[a-z]+', text):
        return True
    else:
        return False
