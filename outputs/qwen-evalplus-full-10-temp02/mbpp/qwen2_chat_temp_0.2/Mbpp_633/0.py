def pair_xor_Sum(arr, n):
    # Initialize the sum of XOR to 0
    xor_sum = 0
    
    # Iterate through each element in the array
    for i in range(n):
        # Iterate through each element in the array again
        for j in range(i + 1, n):
            # Calculate the XOR of the current element and the next element
            xor = arr[i] ^ arr[j]
            # Add the XOR to the sum
            xor_sum += xor
    
    # Return the total sum of XOR
    return xor_sum