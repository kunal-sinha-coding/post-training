def hexagonal_num(n):
    """
    Calculate the nth hexagonal number.
    
    Args:
    n (int): The position in the sequence of hexagonal numbers.
    
    Returns:
    int: The nth hexagonal number.
    """
    return n * (2 * n - 1)