def min_Swaps(binary1, binary2):
    # Initialize the count of swaps
    swaps = 0
    
    # Iterate through the binary strings
    for i in range(len(binary1)):
        # If the characters at the current positions are different, increment the swap count
        if binary1[i] != binary2[i]:
            swaps += 1
    
    return swaps