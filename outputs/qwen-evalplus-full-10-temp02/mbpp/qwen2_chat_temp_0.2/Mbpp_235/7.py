def even_bit_set_number(number):
    # Initialize the result to 0
    result = 0
    # Iterate through each bit of the number
    for i in range(32):  # 32 bits in a 32-bit integer
        # Check if the current bit is even
        if (number >> i) & 1 == 0:
            # Set the corresponding bit in the result
            result |= (1 << i)
    return result