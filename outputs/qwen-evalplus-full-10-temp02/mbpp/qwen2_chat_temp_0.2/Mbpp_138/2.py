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
    
    # Initialize the sum to 0
    sum_of_powers = 0
    
    # Loop until n becomes 0
    while n > 0:
        # Check if the last bit of n is 1
        if n % 2 == 1:
            # If the sum of powers is greater than or equal to n, return False
            if sum_of_powers >= n:
                return False
            # Add 2 to the sum of powers
            sum_of_powers += 2
        # Remove the last bit of n
        n //= 2
    
    # If the loop completes without returning False, return True
    return True