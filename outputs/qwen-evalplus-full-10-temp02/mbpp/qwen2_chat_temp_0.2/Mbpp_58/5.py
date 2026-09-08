def opposite_Signs(x, y):
    """
    Check if the given two integers have opposite sign.
    
    Args:
    x (int): The first integer.
    y (int): The second integer.
    
    Returns:
    bool: True if the signs of x and y are opposite, False otherwise.
    """
    return x < 0 and y > 0 or x > 0 and y < 0