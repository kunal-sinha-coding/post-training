def is_polite(n):
    """
    This function checks if the nth polite number is a prime number.
    """
    # Base case: if n is 1, the only prime number is 1
    if n == 1:
        return True
    
    # Initialize a counter for prime numbers
    prime_count = 0
    
    # Iterate through numbers starting from 2
    for num in range(2, n + 1):
        # Check if the number is prime
        if is_prime(num):
            prime_count += 1
    
    # If prime_count is equal to n, return True, otherwise False
    return prime_count == n
