def set_left_most_unset_bit(n):
    # Initialize the result to 0
    result = 0
    # Loop through each bit in the number
    for i in range(32):
        # Check if the current bit is unset
        if (n & (1 << i)) == 0:
            # Set the result to the current bit
            result |= (1 << i)
    return result