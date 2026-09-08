def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    Parameters:
    n (int): The position in the sequence of centered hexagonal numbers.
    
    Returns:
    int: The nth centered hexagonal number.
    
    Examples:
    >>> centered_hexagonal_number(10)
    271
    >>> centered_hexagonal_number(1)
    1
    >>> centered_hexagonal_number(2)
    5
    >>> centered_hexagonal_number(3)
    13
    >>> centered_hexagonal_number(4)
    25
    >>> centered_hexagonal_number(5)
    37
    """
    return n * (2 * n - 1) + 1
