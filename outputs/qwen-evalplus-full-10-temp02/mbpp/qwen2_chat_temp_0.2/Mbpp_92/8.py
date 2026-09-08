def is_undulating(n):
    """
    Check if the given number is undulating.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if the number is undulating, False otherwise.
    """
    # Check if the number is a perfect square
    if int(n**0.5)**2 == n:
        return True
    else:
        return False
