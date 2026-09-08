def differ_At_One_Bit_Pos(num1, num2):
    # Convert the numbers to binary strings
    bin1 = bin(num1)[2:]
    bin2 = bin(num2)[2:]
    
    # Compare the binary strings
    if bin1 != bin2:
        return True
    else:
        return False