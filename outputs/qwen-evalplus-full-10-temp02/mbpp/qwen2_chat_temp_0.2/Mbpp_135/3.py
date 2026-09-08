def hexagonal_num(n):
    """
    Calculate the nth hexagonal number.
    
    Args:
    n (int): The position in the sequence of hexagonal numbers.
    
    Returns:
    int: The nth hexagonal number.
    
    Examples:
    >>> hexagonal_num(10)
    190
    >>> hexagonal_num(1)
    1
    >>> hexagonal_num(2)
    6
    >>> hexagonal_num(3)
    15
    >>> hexagonal_num(4)
    25
    >>> hexagonal_num(5)
    35
    """
    return n * (2 * n - 1)
