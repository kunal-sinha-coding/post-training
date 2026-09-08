def power(a, b):
    # Initialize the result to 1 (since any number to the power of 0 is 1)
    result = 1
    # Loop through each bit of 'b'
    for i in range(b):
        # Multiply the result by 'a' raised to the power of the current bit
        result *= a
    # Return the final result
    return result