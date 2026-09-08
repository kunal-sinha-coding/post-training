def count_Primes_nums(n):
    """
    This function counts the number of prime numbers less than a given non-negative number n.
    
    Args:
    n (int): A non-negative integer.
    
    Returns:
    int: The count of prime numbers less than n.
    """
    count = 0
    for i in range(2, n):
        if is_prime(i):
            count += 1
    return count

def is_prime(num):
    """
    This helper function checks if a number is prime.
    
    Args:
    num (int): A number to check.
    
    Returns:
    bool: True if the number is prime, False otherwise.
    """
    if num <= 1:
        return False
    if num <= 3:
        return True
    if num % 2 == 0 or num % 3 == 0:
        return False
    i = 5
    while i * i <= num:
        if num % i == 0 or num % (i + 2) == 0:
            return False
        i += 6
    return True