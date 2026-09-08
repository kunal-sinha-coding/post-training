def max_Abs_Diff(arr):
    # Initialize the minimum and maximum differences
    min_diff = float('inf')
    max_diff = float('-inf')
    
    # Iterate through the array to find the minimum and maximum differences
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            diff = abs(arr[i] - arr[j])
            if diff < min_diff:
                min_diff = diff
            if diff > max_diff:
                max_diff = diff
    
    # Return the maximum difference found
    return max_diff