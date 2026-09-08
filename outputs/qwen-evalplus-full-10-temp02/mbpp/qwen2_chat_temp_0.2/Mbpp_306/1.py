def max_sum_increasing_subseq(nums, k, i, n):
    # Initialize the maximum sum to 0
    max_sum = 0
    # Initialize the current sum to 0
    current_sum = 0
    # Iterate through the array starting from the given index
    for j in range(i, n):
        # If the current element is greater than the current sum, update the current sum
        if nums[j] > current_sum:
            current_sum = nums[j]
        # Update the maximum sum if the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            max_sum = current_sum
    # Return the maximum sum found
    return max_sum