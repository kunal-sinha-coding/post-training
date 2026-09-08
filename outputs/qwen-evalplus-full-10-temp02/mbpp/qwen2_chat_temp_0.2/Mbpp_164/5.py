def are_equivalent(dividend, divisor):
    """
    Determine if the sum of the divisors of two integers are the same.
    
    Args:
    dividend (int): The first integer.
    divisor (int): The second integer.
    
    Returns:
    bool: True if the sum of the divisors is the same, False otherwise.
    """
    # Calculate the sum of the divisors of both numbers
    sum_divisors = (dividend + divisor) // 2
    
    # Check if the sum of the divisors is equal to the original dividend
    return sum_divisors == dividend
