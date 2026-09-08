def jacobsthal_num(n):
    """
    Calculate the nth jacobsthal number.
    
    Args:
    n (int): The position in the sequence of jacobsthal numbers.
    
    Returns:
    int: The nth jacobsthal number.
    """
    # Base cases
    if n == 0:
        return 0
    elif n == 1:
        return 1
    elif n == 2:
        return 1
    
    # Initialize the first three jacobsthal numbers
    jacobsthal = [0, 1, 1]
    
    # Calculate the jacobsthal numbers up to the nth number
    for i in range(3, n + 1):
        next_value = jacobsthal[i - 1] + jacobsthal[i - 2]
        jacobsthal.append(next_value)
    
    return jacobsthal[n]
