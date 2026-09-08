def opposite_Signs(x, y):
    """
    Check whether the given two integers have opposite sign or not.
    
    Args:
    x (int): The first integer.
    y (int): The second integer.
    
    Returns:
    bool: True if the signs of x and y are opposite, False otherwise.
    """
    # Check if the signs of x and y are opposite
    return x < 0 != y < 0