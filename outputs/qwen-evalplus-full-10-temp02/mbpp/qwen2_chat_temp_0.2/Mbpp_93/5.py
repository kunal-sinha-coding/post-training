def power(a, b):
    # Initialize the result to 1
    result = 1
    # Loop through each bit of 'b'
    for i in range(b):
        # Multiply the result by 'a' raised to the power of 'i'
        result *= a
    # Return the final result
    return result