def find_star_num(n):
    """
    Find the n'th star number.
    
    Args:
    n (int): The position of the star in the sequence.
    
    Returns:
    int: The n'th star number.
    """
    # Base case: the first star is 1
    if n == 1:
        return 1
    
    # Recursive case: the n'th star number is the sum of the n-1 stars and the n-2 stars
    return find_star_num(n-1) + find_star_num(n-2)