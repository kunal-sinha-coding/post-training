def tetrahedral_number(n):
    """
    Calculate the nth tetrahedral number.
    
    Args:
    n (int): The position in the sequence of tetrahedral numbers.
    
    Returns:
    int: The nth tetrahedral number.
    """
    # Base case: the first tetrahedral number is 1
    if n == 1:
        return 1
    # Recursive case: the nth tetrahedral number is n + (n-1) + (n-2)
    else:
        return n + (n-1) + (n-2)
