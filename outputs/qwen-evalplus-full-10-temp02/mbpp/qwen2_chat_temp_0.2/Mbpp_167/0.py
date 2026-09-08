def next_power_of_2(n):
    # Initialize the result to 1 (the smallest power of 2)
    result = 1
    
    # Loop until the result is greater than or equal to n
    while result < n:
        # Double the result
        result *= 2
    
    # Return the result
    return result