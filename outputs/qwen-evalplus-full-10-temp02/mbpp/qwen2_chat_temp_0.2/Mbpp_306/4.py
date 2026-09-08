def max_sum_increasing_subseq(arr, k, i, n):
    # Initialize the maximum sum to 0
    max_sum = 0
    # Initialize the current sum to 0
    current_sum = 0
    # Initialize the maximum sum found so far to 0
    max_found = 0
    
    # Iterate through the array starting from the given index
    for j in range(i, n):
        # If the current element is greater than the current sum, update the current sum
        if arr[j] > current_sum:
            current_sum = arr[j]
        # If the current element is greater than the maximum sum found so far, update the maximum sum found so far
        if current_sum > max_found:
            max_found = current_sum
        # If the current element is greater than the sum of the subsequence ending at i and including k, update the maximum sum found so far
        if current_sum + arr[k] > max_found:
            max_found = current_sum + arr[k]
    
    # Return the maximum sum found so far
    return max_found