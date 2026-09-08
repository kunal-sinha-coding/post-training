def max_sum_increasing_subseq(nums, k, i, n):
    # Initialize the maximum sum to 0
    max_sum = 0
    
    # Iterate through the array starting from the given index
    for j in range(i, n):
        # If the current element is greater than the previous element, update the maximum sum
        if nums[j] > nums[j - 1]:
            max_sum = max(max_sum, nums[j])
    
    # Return the maximum sum found
    return max_sum
