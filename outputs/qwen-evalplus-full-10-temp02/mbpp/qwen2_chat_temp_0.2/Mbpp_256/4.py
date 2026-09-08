def count_Primes_nums(n):
    """
    This function takes a non-negative integer n and returns the number of prime numbers less than n.
    
    Args:
    n (int): A non-negative integer.
    
    Returns:
    int: The count of prime numbers less than n.
    """
    if n < 2:
        return 0
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(i**0.5) + 1)):
            count += 1
    return count