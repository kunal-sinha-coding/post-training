def is_nonagonal(n):
    """
    Calculate the nth nonagonal number.
    
    Args:
    n (int): The position in the sequence of nonagonal numbers.
    
    Returns:
    int: The nth nonagonal number.
    """
    # The nth nonagonal number is given by the formula: n * (n + 1) / 2
    return n * (n + 1) // 2