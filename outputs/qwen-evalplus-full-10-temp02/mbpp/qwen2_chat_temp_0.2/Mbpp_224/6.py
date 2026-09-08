def count_Set_Bits(n):
    # Initialize the count of set bits to 0
    count = 0
    # Loop through each bit in the number
    while n > 0:
        # If the least significant bit is 1, increment the count
        if n & 1 == 1:
            count += 1
        # Right shift the number to check the next bit
        n >>= 1
    # Return the total count of set bits
    return count