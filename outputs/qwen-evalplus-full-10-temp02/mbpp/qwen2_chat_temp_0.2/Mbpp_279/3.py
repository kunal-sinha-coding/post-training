def is_num_decagonal(n):
    """
    This function calculates the nth decagonal number.
    
    Args:
    n (int): The position in the sequence of decagonal numbers.
    
    Returns:
    int: The nth decagonal number.
    """
    # The nth decagonal number is given by the formula: n * (3n - 1) / 2
    return n * (3 * n - 1) // 2
