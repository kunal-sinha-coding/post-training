def check_integer(s):
    """
    Check if the given string is an integer.
    
    Args:
    s (str): The string to check.
    
    Returns:
    bool: True if the string is an integer, False otherwise.
    """
    # Check if the string is empty or consists only of non-numeric characters
    if not s or not s.isdigit():
        return False
    # Check if the string is a valid integer
    try:
        int(s)
        return True
    except ValueError:
        return False