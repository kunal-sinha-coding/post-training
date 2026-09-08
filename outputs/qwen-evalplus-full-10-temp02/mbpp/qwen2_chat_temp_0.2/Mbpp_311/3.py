def set_left_most_unset_bit(n):
    # Initialize the result with the same value as n
    result = n
    # Set the leftmost unset bit by performing a bitwise AND operation
    result &= (result - 1)
    return result