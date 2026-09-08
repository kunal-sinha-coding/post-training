def is_Sum_Of_Powers_Of_Two(n):
    # If n is less than 1, it cannot be represented as sum of powers of 2
    if n < 1:
        return False
    
    # Initialize the sum to 0
    sum_of_powers = 0
    
    # Loop until n becomes 0
    while n > 0:
        # Check if n is a power of 2
        if n % 2 == 0:
            # Add the power of 2 to the sum
            sum_of_powers += 1
            # Divide n by 2
            n //= 2
        else:
            # If n is not a power of 2, return False
            return False
    
    # If n is 0, return True
    return True