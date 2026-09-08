def differ_At_One_Bit_Pos(num1, num2):
    # Convert both numbers to binary and remove the '0b' prefix
    bin1 = bin(num1)[2:]
    bin2 = bin(num2)[2:]
    
    # Compare the binary representations of the two numbers
    if bin1 != bin2:
        return True
    else:
        return False