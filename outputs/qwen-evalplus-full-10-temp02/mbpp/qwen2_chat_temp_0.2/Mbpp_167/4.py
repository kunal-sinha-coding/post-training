def next_power_of_2(n):
    """
    Find the smallest power of 2 greater than or equal to n.
    
    Args:
    n (int): The number to find the next power of 2 for.
    
    Returns:
    int: The smallest power of 2 greater than or equal to n.
    """
    # If n is 0, return 1
    if n == 0:
        return 1
    # Calculate the next power of 2 using the ceiling function
    return (1 << (n + 1)) - 1