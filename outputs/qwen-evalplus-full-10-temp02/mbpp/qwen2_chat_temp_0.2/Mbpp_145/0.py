def max_Abs_Diff(arr):
    # Initialize the minimum and maximum differences
    min_diff = arr[1] - arr[0]
    max_diff = arr[1] - arr[0]
    
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the minimum difference if the current element is smaller
        if arr[i] < min_diff:
            min_diff = arr[i]
        # Update the maximum difference if the current element is larger
        if arr[i] > max_diff:
            max_diff = arr[i]
    
    # Return the maximum difference found
    return max_diff