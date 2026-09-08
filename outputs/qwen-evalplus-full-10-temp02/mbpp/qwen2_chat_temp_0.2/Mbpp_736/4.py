def left_insertion(arr, x):
    # Initialize the insertion point to the first element of the array
    i = 0
    # Iterate through the array starting from the second element
    while i < len(arr):
        # If the current element is greater than or equal to x, move the insertion point to the current index
        if arr[i] >= x:
            i += 1
        else:
            # If the current element is less than x, break the loop
            break
    # Return the insertion point
    return i