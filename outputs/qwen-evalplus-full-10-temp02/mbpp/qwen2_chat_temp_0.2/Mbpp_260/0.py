def newman_prime(n):
    """
    Find the nth Newman–Shanks–Williams prime number.
    
    Args:
    n (int): The position in the sequence of Newman–Shanks–Williams primes.
    
    Returns:
    int: The nth Newman–Shanks–Williams prime number.
    """
    # Initialize the first two Newman–Shanks–Williams primes
    a, b = 2, 3
    # Generate the sequence of Newman–Shanks–Williams primes
    while True:
        # Calculate the next Newman–Shanks–Williams prime
        c = (a + b) % 1000000007
        a, b = b, c
        # Check if the current prime is a Newman–Shanks–Williams prime
        if is_newman_shanks_williams_prime(c):
            return c