def last(arr, x):
    # Initialize the last position to -1
    last = -1
    # Iterate through the array from the end
    for i in range(len(arr) - 1, -1, -1):
        # If the current element is equal to x, update the last position
        if arr[i] == x:
            last = i
    # Return the last position found
    return last