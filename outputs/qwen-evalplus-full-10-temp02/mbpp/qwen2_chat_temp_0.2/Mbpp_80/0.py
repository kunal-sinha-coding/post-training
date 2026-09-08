def tetrahedral_number(n):
    """
    Calculate the nth tetrahedral number.
    
    Args:
    n (int): The position in the sequence of tetrahedral numbers.
    
    Returns:
    int: The nth tetrahedral number.
    
    Examples:
    >>> tetrahedral_number(5)
    35
    >>> tetrahedral_number(6)
    84
    >>> tetrahedral_number(7)
    144
    """
    return n * (n + 1) * (n + 2) // 6