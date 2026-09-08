def pair_xor_Sum(arr, n):
    # Initialize the sum to 0
    sum = 0
    # Iterate through each element in the array
    for i in range(n):
        # Iterate through each element in the array again
        for j in range(i + 1, n):
            # Calculate the XOR of the current element and the next element
            xor = arr[i] ^ arr[j]
            # Add the XOR to the sum
            sum += xor
    # Return the final sum
    return sum