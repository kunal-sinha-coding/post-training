def find_min_diff(arr, n):
    # Sort the array to make it easier to find the minimum difference
    arr.sort()
    # Initialize the minimum difference to a large number
    min_diff = float('inf')
    # Iterate through the array to find the minimum difference
    for i in range(n):
        # Calculate the difference between consecutive elements
        diff = arr[i+1] - arr[i]
        # Update the minimum difference if the current difference is smaller
        if diff < min_diff:
            min_diff = diff
    # Return the minimum difference found
    return min_diff