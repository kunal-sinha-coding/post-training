def next_power_of_2(n):
    """
    Find the smallest power of 2 greater than or equal to n.
    
    Parameters:
    n (int): The number to find the next power of 2 for.
    
    Returns:
    int: The smallest power of 2 greater than or equal to n.
    """
    # Initialize the result to 1 (since 2^0 is 1)
    result = 1
    
    # Loop until the result is greater than or equal to n
    while result < n:
        result *= 2
    
    return result