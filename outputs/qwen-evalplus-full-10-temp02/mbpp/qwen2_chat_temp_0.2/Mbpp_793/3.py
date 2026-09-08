def last(arr, x):
    # Initialize the last position to -1 (indicating the element is not found)
    last = -1
    # Iterate through the array from the end to the beginning
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is equal to the target element
        if arr[i] == x:
            # Update the last position if the current element is greater than the last found position
            last = i
    # Return the last position of the element
    return last