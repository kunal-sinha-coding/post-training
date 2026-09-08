def find_star_num(n):
    """
    Calculate the n'th star number.
    
    Args:
    n (int): The position of the star in the sequence.
    
    Returns:
    int: The n'th star number.
    """
    # Base case: the first star is 1
    if n == 1:
        return 1
    # Recursive case: the n'th star number is n^2 - 1
    else:
        return n**2 - 1
