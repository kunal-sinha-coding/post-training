def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    Parameters:
    n (int): The position in the sequence of centered hexagonal numbers.
    
    Returns:
    int: The nth centered hexagonal number.
    """
    # The nth centered hexagonal number is given by the formula: 2n^2 - n + 1
    return 2 * n**2 - n + 1
