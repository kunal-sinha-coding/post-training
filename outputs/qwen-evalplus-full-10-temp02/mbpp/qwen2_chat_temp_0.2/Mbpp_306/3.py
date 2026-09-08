def max_sum_increasing_subseq(arr, k, i, n):
    # Initialize the maximum sum to 0
    max_sum = 0
    
    # Iterate through the array starting from the given index
    for j in range(i, n):
        # Check if the current element is greater than the maximum sum found so far
        if arr[j] > max_sum:
            # Update the maximum sum
            max_sum = arr[j]
    
    # Return the maximum sum found
    return max_sum