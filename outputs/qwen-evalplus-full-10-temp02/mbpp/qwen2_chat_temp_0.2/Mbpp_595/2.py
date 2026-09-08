def min_Swaps(binary1, binary2):
    # Initialize a counter for the number of swaps needed
    swaps = 0
    
    # Iterate through the strings
    for i in range(len(binary1)):
        # If the characters at the current positions are different, increment the swap counter
        if binary1[i] != binary2[i]:
            swaps += 1
    
    return swaps