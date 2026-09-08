def pair_xor_Sum(arr, n):
    # Initialize the sum of XOR of all pairs
    total_xor = 0
    
    # Iterate through each element in the array
    for i in range(n):
        # Iterate through each element in the array again
        for j in range(i + 1, n):
            # Calculate the XOR of the current pair
            xor_value = arr[i] ^ arr[j]
            # Add the XOR value to the total sum
            total_xor += xor_value
    
    # Return the total sum of XOR of all pairs
    return total_xor