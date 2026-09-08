def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    A centered hexagonal number is defined as the sum of the first n natural numbers.
    The formula for the nth centered hexagonal number is:
    n * (n + 1) * (2 * n + 1) / 6
    
    Parameters:
    n (int): The position of the centered hexagonal number to calculate.
    
    Returns:
    int: The nth centered hexagonal number.
    """
    return n * (n + 1) * (2 * n + 1) // 6
