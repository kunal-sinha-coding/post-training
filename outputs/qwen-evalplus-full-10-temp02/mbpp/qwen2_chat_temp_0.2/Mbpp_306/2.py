def max_sum_increasing_subseq(arr, n, k, i):
    # Initialize the maximum sum to 0
    max_sum = 0
    
    # Iterate through the array starting from the current index
    for j in range(i, n):
        # Check if the current element is greater than the previous element
        if arr[j] > arr[j - 1]:
            # Update the maximum sum if the current element is greater
            max_sum = max(max_sum, arr[j])
    
    # Return the maximum sum found
    return max_sum
