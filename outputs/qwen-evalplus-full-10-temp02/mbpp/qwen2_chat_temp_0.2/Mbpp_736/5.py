def left_insertion(arr, x):
    # Initialize the insertion point
    i = 0
    # Iterate through the array to find the correct position
    while i < len(arr) and arr[i] < x:
        i += 1
    # Return the index of the insertion point
    return i