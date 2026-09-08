def pair_xor_Sum(nums, n):
    # Initialize the sum of xor of all pairs
    xor_sum = 0
    
    # Iterate through each pair of numbers in the list
    for i in range(n):
        for j in range(i + 1, n):
            # Calculate the xor of the current pair
            xor_value = nums[i] ^ nums[j]
            # Add the xor value to the sum
            xor_sum += xor_value
    
    return xor_sum