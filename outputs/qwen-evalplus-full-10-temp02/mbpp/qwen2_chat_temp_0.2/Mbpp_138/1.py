def is_Sum_Of_Powers_Of_Two(n):
    """
    Check if the given number can be represented as sum of non-zero powers of 2.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if n can be represented as sum of non-zero powers of 2, False otherwise.
    """
    # If n is less than 1, it cannot be represented as sum of powers of 2
    if n < 1:
        return False
    
    # If n is 1, it can be represented as 1^0 = 1
    if n == 1:
        return True
    
    # If n is even, it cannot be represented as sum of powers of 2
    if n % 2 == 0:
        return False
    
    # If n is odd, check if it can be expressed as sum of powers of 2
    # The expression n = 2^k + 2^(k-1) + ... + 2^1 + 2^0
    # This is equivalent to n = 2^k + (2^(k-1) + ... + 2^1) + 2^0
    # which is 2^(k+1) - 1
    # If n is odd, 2^(k+1) - 1 is not equal to n, so n cannot be represented as sum of powers of 2
    return n % 2 != 0
