def power(a, b):
    # Initialize the result to 1 (since any number to the power of 0 is 1)
    result = 1
    # Loop through each iteration of b
    for _ in range(b):
        # Multiply the result by 'a' at each iteration
        result *= a
    # Return the final result
    return result