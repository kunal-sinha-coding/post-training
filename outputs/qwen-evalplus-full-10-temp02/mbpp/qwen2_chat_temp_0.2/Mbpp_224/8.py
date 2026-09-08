def count_Set_Bits(n):
    # Initialize the count of set bits to 0
    count = 0
    # Loop through each bit in the number
    while n:
        # Increment the count if the current bit is 1
        count += n & 1
        # Right shift the number to check the next bit
        n >>= 1
    # Return the total count of set bits
    return count