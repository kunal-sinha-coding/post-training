def power(a, b):
    # Initialize the result to 1 (since any number to the power of 0 is 1)
    result = 1
    # Loop through each bit of 'b'
    for i in range(b):
        # Multiply the result by 'a' and shift the bit to the left by 1
        result *= a
        # Right shift the bit by 1
        a >>= 1
    return result