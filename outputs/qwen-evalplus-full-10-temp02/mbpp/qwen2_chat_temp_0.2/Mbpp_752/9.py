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
    jacobsthal_0 = 0
    jacobsthal_1 = 1
    jacobsthal_2 = 1
    jacobsthal_n = 0
    
    # Calculate the nth jacobsthal number iteratively
    for i in range(3, n + 1):
        jacobsthal_n = jacobsthal_0 + jacobsthal_1 + jacobsthal_2
        jacobsthal_0 = jacobsthal_1
        jacobsthal_1 = jacobsthal_2
        jacobsthal_2 = jacobsthal_n
    
    return jacobsthal_n