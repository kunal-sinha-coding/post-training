def count_Primes_nums(n):
    """
    This function takes a non-negative integer n and returns the number of prime numbers less than n.
    
    Args:
    n (int): A non-negative integer.
    
    Returns:
    int: The count of prime numbers less than n.
    """
    if n <= 1:
        return 0
    count = 0
    for num in range(2, n):
        if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
            count += 1
    return count