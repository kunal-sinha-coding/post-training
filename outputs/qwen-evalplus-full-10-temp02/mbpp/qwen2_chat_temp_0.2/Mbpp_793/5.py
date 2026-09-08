def last(arr, x):
    # Initialize the last position to -1
    last = -1
    # Iterate through the array starting from the end
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is equal to the target element
        if arr[i] == x:
            # Update the last position if the current element is greater than the last found position
            last = i
    # Return the last position found
    return last