def differ_At_One_Bit_Pos(num1, num2):
    # Convert numbers to binary strings and remove the '0b' prefix
    bin1 = bin(num1)[2:]
    bin2 = bin(num2)[2:]
    
    # Compare the binary strings
    if bin1 != bin2:
        return True
    else:
        return False