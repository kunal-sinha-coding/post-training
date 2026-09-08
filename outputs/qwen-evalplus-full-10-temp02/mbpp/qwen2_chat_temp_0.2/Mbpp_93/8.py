def power(a, b):
    # Initialize the result to 1
    result = 1
    # Loop through each bit of 'b'
    for _ in range(b):
        # Multiply the result by 'a'
        result *= a
    # Return the final result
    return result