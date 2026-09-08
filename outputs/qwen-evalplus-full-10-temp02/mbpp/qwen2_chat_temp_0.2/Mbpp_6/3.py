def differ_At_One_Bit_Pos(num1, num2):
    # Convert the numbers to binary and remove the '0b' prefix
    bin1 = bin(num1)[2:]
    bin2 = bin(num2)[2:]
    
    # Initialize a counter for differing bits
    differing_bits = 0
    
    # Iterate through the binary strings
    for bit1, bit2 in zip(bin1, bin2):
        # If the bits are different, increment the counter
        if bit1 != bit2:
            differing_bits += 1
    
    # Return True if there are exactly one differing bit, otherwise False
    return differing_bits == 1