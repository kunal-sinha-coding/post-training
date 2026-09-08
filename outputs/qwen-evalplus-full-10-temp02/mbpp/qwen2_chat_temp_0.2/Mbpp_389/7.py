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
    >>> find_lucas(1)
    2
    >>> find_lucas(8)
    29
    """
    # Base cases for the first two lucas numbers
    if n == 0:
        return 2
    elif n == 1:
        return 1
    
    # Initialize the first two lucas numbers
    lucas_1, lucas_2 = 2, 1
    
    # Calculate the lucas numbers iteratively
    for i in range(2, n + 1):
        lucas_next = lucas_1 + lucas_2
        lucas_1, lucas_2 = lucas_2, lucas_next
    
    return lucas_2