def pair_xor_Sum(nums, n):
    # Initialize the sum to 0
    sum_xor = 0
    # Iterate through each number in the list
    for i in range(n):
        # Iterate through each number in the list again
        for j in range(i + 1, n):
            # Calculate the XOR of the current number and the next number
            xor_value = nums[i] ^ nums[j]
            # Add the XOR value to the sum
            sum_xor += xor_value
    # Return the total sum of XOR values
    return sum_xor