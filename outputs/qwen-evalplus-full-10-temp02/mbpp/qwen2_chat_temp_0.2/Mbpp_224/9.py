def count_Set_Bits(n):
    # Initialize a counter for set bits
    set_bits = 0
    # Loop through each bit in the number
    while n > 0:
        # Check if the current bit is set
        if n & 1 == 1:
            set_bits += 1
        # Right shift the number to check the next bit
        n >>= 1
    return set_bits