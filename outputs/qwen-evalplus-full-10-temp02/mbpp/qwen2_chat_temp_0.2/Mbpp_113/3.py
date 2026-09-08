def check_integer(s):
    """
    Check if the given string represents an integer.
    
    Args:
    s (str): The string to check.
    
    Returns:
    bool: True if the string is an integer, False otherwise.
    """
    # Check if the string is empty or contains only digits
    if not s or s.isdigit():
        return True
    else:
        return False