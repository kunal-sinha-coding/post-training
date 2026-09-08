def is_not_prime(n):
    """
    This function checks if a number is not prime.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if the number is not prime, False otherwise.
    """
    if n <= 1:
        return True
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return True
    return False