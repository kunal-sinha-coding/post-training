def even_bit_set_number(number):
    # Initialize a variable to store the result
    result = 0
    # Iterate through each bit of the number
    for i in range(32):  # 32 is the number of bits in a 32-bit integer
        # Check if the current bit is even
        if number & (1 << i) == 0:
            # Set the corresponding bit in the result
            result |= (1 << i)
    return result