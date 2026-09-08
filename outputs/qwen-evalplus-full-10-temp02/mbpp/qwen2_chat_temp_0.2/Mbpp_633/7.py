def pair_xor_Sum(arr, n):
    # Initialize the sum of xor of all pairs
    xor_sum = 0
    
    # Iterate through each element in the array
    for i in range(n):
        # Iterate through each element in the array again
        for j in range(i + 1, n):
            # Calculate the xor of the current pair
            xor = arr[i] ^ arr[j]
            # Add the xor to the sum
            xor_sum += xor
    
    # Return the total sum of xor of all pairs
    return xor_sum