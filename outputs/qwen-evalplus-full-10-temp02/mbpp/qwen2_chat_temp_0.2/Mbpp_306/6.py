def max_sum_increasing_subseq(arr, k, i, n):
    # Initialize the maximum sum to 0
    max_sum = 0
    # Initialize the current sum to 0
    current_sum = 0
    # Iterate through the array starting from the given index
    for j in range(i, n):
        # Update the current sum if the current element is greater than the current sum
        if arr[j] > current_sum:
            current_sum = arr[j]
        # Update the maximum sum if the current sum is greater than the maximum sum found so far
        if current_sum > max_sum:
            max_sum = current_sum
    # Return the maximum sum found
    return max_sum