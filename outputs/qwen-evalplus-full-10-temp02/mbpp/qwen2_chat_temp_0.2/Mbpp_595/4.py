def min_Swaps(binary1, binary2):
    # Initialize the count of swaps needed
    swaps = 0
    
    # Iterate through the binary strings
    for i in range(len(binary1)):
        # If the characters at the current positions are different, swap them
        if binary1[i] != binary2[i]:
            swaps += 1
    
    return swaps