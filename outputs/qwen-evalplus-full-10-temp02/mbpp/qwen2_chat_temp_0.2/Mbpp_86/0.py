def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    Parameters:
    n (int): The position of the centered hexagonal number to find.
    
    Returns:
    int: The nth centered hexagonal number.
    """
    # The formula for the nth centered hexagonal number is n * (2 * n + 1)
    return n * (2 * n + 1)
