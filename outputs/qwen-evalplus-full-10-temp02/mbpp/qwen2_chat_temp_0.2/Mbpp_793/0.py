def last(arr, x):
    # Initialize the last index to -1
    last = -1
    # Iterate through the array from the end
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is equal to x
        if arr[i] == x:
            # Update the last index to the current index
            last = i
            # Return the last index
            return last
    # Return -1 if x is not found in the array
    return -1