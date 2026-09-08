def differ_At_One_Bit_Pos(num1, num2):
    # Convert the numbers to binary strings
    bin1 = bin(num1)[2:]  # Remove the '0b' prefix
    bin2 = bin(num2)[2:]  # Remove the '0b' prefix
    
    # Compare the binary strings
    if bin1 == bin2:
        return False  # If the binary strings are the same, they differ at one bit position
    else:
        return True  # If the binary strings are different, they do not differ at one bit position