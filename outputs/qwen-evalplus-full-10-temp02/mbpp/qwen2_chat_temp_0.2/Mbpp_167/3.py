def next_power_of_2(n):
    """
    Find the smallest power of 2 greater than or equal to n.
    
    Parameters:
    n (int): The number to find the next power of 2 for.
    
    Returns:
    int: The smallest power of 2 greater than or equal to n.
    """
    # If n is 0, return 1 because 2^0 is 1.
    if n == 0:
        return 1
    # Calculate the next power of 2 using the ceiling function.
    return 2 ** (n + 1)