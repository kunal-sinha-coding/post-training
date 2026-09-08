def max_Abs_Diff(arr):
    # Initialize the minimum and maximum difference to a large number
    min_diff = float('inf')
    max_diff = float('-inf')
    
    # Iterate through the array to find the minimum and maximum differences
    for i in range(len(arr)):
        for j in range(i + 1, len(arr)):
            # Calculate the absolute difference between arr[i] and arr[j]
            diff = abs(arr[i] - arr[j])
            # Update the minimum and maximum differences if the current difference is smaller
            if diff < min_diff:
                min_diff = diff
            if diff > max_diff:
                max_diff = diff
    
    # Return the maximum difference found
    return max_diff