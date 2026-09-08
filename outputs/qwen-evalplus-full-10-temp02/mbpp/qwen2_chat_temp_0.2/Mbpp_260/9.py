def newman_prime(n):
    """
    Find the nth newman–shanks–williams prime number.
    
    Args:
    n (int): The position in the sequence of newman–shanks–williams primes.
    
    Returns:
    int: The nth newman–shanks–williams prime number.
    """
    # Base case: the first newman–shanks–williams prime is 2
    if n == 1:
        return 2
    
    # Initialize the first two newman–shanks–williams primes
    a, b = 2, 3
    
    # Generate the sequence of newman–shanks–williams primes
    for _ in range(2, n):
        next_prime = a + b
        a, b = b, next_prime
    
    return next_prime