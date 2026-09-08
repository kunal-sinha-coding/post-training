def pair_xor_Sum(lst, n):
    # Initialize the sum of xor of all pairs
    xor_sum = 0
    
    # Iterate through each pair of numbers in the list
    for i in range(n):
        for j in range(i + 1, n):
            # Calculate the xor of the current pair
            xor = lst[i] ^ lst[j]
            # Add the xor to the sum
            xor_sum += xor
    
    return xor_sum