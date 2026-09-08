def is_octagonal(n):
    """
    This function calculates the nth octagonal number.
    
    Args:
    n (int): The position in the octagonal sequence.
    
    Returns:
    int: The nth octagonal number.
    """
    # The nth octagonal number is given by the formula: n * (n + 1) / 2
    return n * (n + 1) // 2
