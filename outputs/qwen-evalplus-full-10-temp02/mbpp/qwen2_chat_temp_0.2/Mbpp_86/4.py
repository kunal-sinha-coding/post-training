def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    Parameters:
    n (int): The position in the sequence of centered hexagonal numbers.
    
    Returns:
    int: The nth centered hexagonal number.
    """
    # Formula to calculate the nth centered hexagonal number
    return n * (2 * n - 1)
