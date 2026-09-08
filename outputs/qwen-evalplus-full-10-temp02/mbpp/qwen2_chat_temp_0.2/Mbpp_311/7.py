def set_left_most_unset_bit(n):
    # Initialize the result with the least significant bit set
    result = n & (n - 1)
    # Right shift the result by 1 to set the leftmost unset bit
    result >>= 1
    return result