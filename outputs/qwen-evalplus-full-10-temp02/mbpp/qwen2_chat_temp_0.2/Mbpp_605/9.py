def prime_num(num):
    """
    Check if the given integer is a prime number.
    
    Args:
    num (int): The integer to check.
    
    Returns:
    bool: True if the number is prime, False otherwise.
    
    Examples:
    >>> prime_num(13)
    True
    >>> prime_num(14)
    False
    """
    if num <= 1:
        return False
    for i in range(2, int(num**0.5) + 1):
        if num % i == 0:
            return False
    return True