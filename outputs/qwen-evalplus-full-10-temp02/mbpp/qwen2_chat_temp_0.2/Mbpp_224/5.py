def count_Set_Bits(n):
    # Initialize a counter for set bits
    count = 0
    # Loop through each bit of the number
    while n:
        # Increment the counter if the current bit is set
        count += n & 1
        # Right shift the number to check the next bit
        n >>= 1
    # Return the total count of set bits
    return count