def differ_At_One_Bit_Pos(num1, num2):
    # XOR operation to find the differing bits
    result = num1 ^ num2
    # Check if the result is 0
    if result == 0:
        return True
    else:
        return False