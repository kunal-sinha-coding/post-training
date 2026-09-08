def newman_prime(n):
    """
    Find the nth Newman–Shanks–Williams prime number.
    
    Args:
    n (int): The position of the prime number to find.
    
    Returns:
    int: The nth Newman–Shanks–Williams prime number.
    """
    # Initialize the first two Newman–Shanks–Williams primes
    a = 2
    b = 3
    c = 5
    d = 7
    count = 0
    
    # Generate the nth Newman–Shanks–Williams prime
    while count < n:
        next_prime = a + b + c + d
        a, b, c, d = b, c, d, next_prime
        count += 1
    
    return next_prime