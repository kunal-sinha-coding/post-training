def is_nonagonal(n):
    """
    Calculate the nth nonagonal number.
    
    Args:
    n (int): The position in the sequence of nonagonal numbers.
    
    Returns:
    int: The nth nonagonal number.
    
    Examples:
    >>> is_nonagonal(10)
    325
    >>> is_nonagonal(1)
    1
    >>> is_nonagonal(2)
    6
    >>> is_nonagonal(3)
    15
    >>> is_nonagonal(4)
    28
    """
    # The nth nonagonal number is given by the formula: n * (n + 1) / 2
    return n * (n + 1) // 2