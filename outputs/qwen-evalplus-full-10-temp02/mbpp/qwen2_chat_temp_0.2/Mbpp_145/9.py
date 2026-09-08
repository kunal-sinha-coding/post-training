def max_Abs_Diff(arr):
    # Initialize the minimum value to the first element of the array
    min_val = arr[0]
    # Initialize the maximum difference to the first element of the array
    max_diff = arr[0]
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # Update the minimum value if the current element is smaller
        if arr[i] < min_val:
            min_val = arr[i]
        # Update the maximum difference if the current element is larger
        if arr[i] - min_val > max_diff:
            max_diff = arr[i] - min_val
    # Return the maximum difference found
    return max_diff