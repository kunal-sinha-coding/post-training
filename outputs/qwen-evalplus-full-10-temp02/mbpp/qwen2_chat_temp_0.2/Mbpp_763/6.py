def find_min_diff(arr, n):
    # Sort the array
    arr.sort()
    # Initialize the minimum difference to a large number
    min_diff = float('inf')
    # Iterate through the array to find the minimum difference
    for i in range(n-1):
        # Calculate the difference between consecutive elements
        diff = arr[i+1] - arr[i]
        # Update the minimum difference if the current difference is smaller
        if diff < min_diff:
            min_diff = diff
    return min_diff