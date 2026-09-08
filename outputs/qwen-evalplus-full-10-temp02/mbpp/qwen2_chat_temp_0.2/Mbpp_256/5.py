def count_Primes_nums(n):
    """
    This function takes in a non-negative number and returns the number of prime numbers less than the given non-negative number.
    
    Args:
    n (int): A non-negative integer.
    
    Returns:
    int: The count of prime numbers less than n.
    """
    # Initialize a counter for prime numbers
    prime_count = 0
    
    # Check for the smallest prime number, which is 2
    if n >= 2:
        prime_count += 1
    
    # Check for odd numbers starting from 3
    for i in range(3, n, 2):
        # Check if the number is prime
        if is_prime(i):
            prime_count += 1
    
    return prime_count
