def is_nonagonal(n):
    """
    This function calculates the nth nonagonal number.
    
    Args:
    n (int): The position of the nonagonal number to find.
    
    Returns:
    int: The nth nonagonal number.
    """
    # The nth nonagonal number is given by the formula: n * (2 * n + 1) / 2
    return n * (2 * n + 1) // 2