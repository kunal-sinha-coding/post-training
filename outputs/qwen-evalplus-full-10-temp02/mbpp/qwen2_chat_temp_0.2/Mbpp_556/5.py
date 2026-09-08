def find_Odd_Pair(arr, n):
    # Initialize a counter for odd pairs
    odd_count = 0
    # Iterate through the array
    for i in range(n):
        # XOR the current element with the next element
        xor_result = arr[i] ^ arr[i + 1]
        # Check if the XOR result is odd
        if xor_result % 2 != 0:
            # Increment the counter for odd pairs
            odd_count += 1
    # Return the count of odd pairs
    return odd_count