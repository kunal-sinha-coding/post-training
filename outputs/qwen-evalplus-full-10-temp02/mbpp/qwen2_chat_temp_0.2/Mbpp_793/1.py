def last(arr, x):
    # Initialize the last position to -1
    last = -1
    # Iterate through the array from the end
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is equal to the target
        if arr[i] == x:
            # Update the last position to the current index
            last = i
            # Break the loop as we found the target
            break
    # Return the last position found
    return last