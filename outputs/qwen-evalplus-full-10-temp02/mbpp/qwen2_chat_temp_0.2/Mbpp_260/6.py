def newman_prime(n):
    """
    Find the nth Newman–Shanks–Williams prime number.
    
    Parameters:
    n (int): The position in the sequence of Newman–Shanks–Williams primes.
    
    Returns:
    int: The nth Newman–Shanks–Williams prime number.
    """
    # Initialize the first two Newman–Shanks–Williams primes
    a, b = 2, 3
    # Generate the sequence of Newman–Shanks–Williams primes
    while True:
        c = (a + b) % n
        a, b = b, c
        if a == 1:
            return b