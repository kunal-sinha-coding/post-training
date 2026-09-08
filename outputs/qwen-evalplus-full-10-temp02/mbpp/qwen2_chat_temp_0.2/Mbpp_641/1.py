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
    4
    >>> is_nonagonal(3)
    9
    >>> is_nonagonal(4)
    16
    >>> is_nonagonal(5)
    25
    """
    # The nth nonagonal number is given by the formula: n * (2 * n - 1)
    return n * (2 * n - 1)
