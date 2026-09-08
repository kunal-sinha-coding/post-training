def count_Primes_nums(n):
    """
    This function takes a non-negative integer n and returns the number of prime numbers less than n.
    
    Args:
    n (int): A non-negative integer.
    
    Returns:
    int: The count of prime numbers less than n.
    """
    # Initialize a counter for prime numbers
    prime_count = 0
    
    # Iterate through all numbers from 2 to n-1
    for num in range(2, n):
        # Check if the number is prime
        if all(num % i != 0 for i in range(2, int(num**0.5) + 1)):
            prime_count += 1
    
    return prime_count
