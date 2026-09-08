def check_integer(s):
    """
    Check if the given string is an integer.
    
    Args:
    s (str): The string to check.
    
    Returns:
    bool: True if the string is an integer, False otherwise.
    """
    try:
        # Attempt to convert the string to an integer
        int(s)
        return True
    except ValueError:
        # If conversion fails, the string is not an integer
        return False