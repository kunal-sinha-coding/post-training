def is_nonagonal(n):
    """
    Calculate the nth nonagonal number.
    
    Args:
    n (int): The position of the nonagonal number to find.
    
    Returns:
    int: The nth nonagonal number.
    """
    # The nth nonagonal number is given by the formula: n * (3n - 1) / 2
    return n * (3 * n - 1) // 2
