def set_left_most_unset_bit(n):
    # Initialize the result with the same bits as n
    result = n
    # Set the leftmost unset bit to 1
    result |= (1 << (n.bit_length() - 1))
    return result