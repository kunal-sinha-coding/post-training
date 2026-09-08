def differ_At_One_Bit_Pos(num1, num2):
    # Convert numbers to binary strings
    bin1 = bin(num1)[2:]  # Remove the '0b' prefix
    bin2 = bin(num2)[2:]  # Remove the '0b' prefix
    
    # Compare the binary strings
    return bin1 != bin2
