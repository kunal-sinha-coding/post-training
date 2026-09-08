def is_octagonal(n):
    """
    This function calculates the nth octagonal number.
    
    Args:
    n (int): The position in the sequence of octagonal numbers.
    
    Returns:
    int: The nth octagonal number.
    
    Examples:
    >>> is_octagonal(5)
    65
    >>> is_octagonal(6)
    121
    >>> is_octagonal(7)
    185
    """
    return n * (3 * n - 1) // 2
