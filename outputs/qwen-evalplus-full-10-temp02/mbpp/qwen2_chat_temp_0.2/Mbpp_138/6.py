def is_Sum_Of_Powers_Of_Two(n):
    """
    Check if the given number can be represented as sum of non-zero powers of 2.
    
    Args:
    n (int): The number to check.
    
    Returns:
    bool: True if n can be represented as sum of non-zero powers of 2, False otherwise.
    """
    # If n is less than 1, it cannot be represented as sum of powers of 2
    if n < 1:
        return False
    
    # Initialize the sum of powers of 2
    sum_of_powers = 0
    
    # While n is greater than 0
    while n > 0:
        # If n is even, add 2 to the sum of powers of 2
        if n % 2 == 0:
            sum_of_powers += 2
            n //= 2
        else:
            # If n is odd, add 1 to the sum of powers of 2
            sum_of_powers += 1
            n -= 1
    
    # If the sum of powers of 2 is equal to n, return True
    return sum_of_powers == n