def find_lucas(n):
    """
    Calculate the n'th lucas number.
    
    Args:
    n (int): The position in the lucas sequence.
    
    Returns:
    int: The n'th lucas number.
    
    Examples:
    >>> find_lucas(9)
    76
    >>> find_lucas(10)
    193
    >>> find_lucas(1)
    2
    >>> find_lucas(2)
    3
    """
    if n == 0:
        return 2
    elif n == 1:
        return 3
    else:
        lucas_sequence = [2, 3]
        for i in range(2, n):
            next_value = lucas_sequence[-1] + lucas_sequence[-2]
            lucas_sequence.append(next_value)
        return lucas_sequence[-1]