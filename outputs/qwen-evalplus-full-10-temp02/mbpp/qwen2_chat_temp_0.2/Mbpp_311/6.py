def set_left_most_unset_bit(n):
    # Initialize the result with the same value as n
    result = n
    
    # Loop through each bit of n
    for i in range(32):
        # Check if the current bit is unset
        if (n & (1 << i)) == 0:
            # Set the leftmost unset bit
            result |= (1 << i)
    
    return result