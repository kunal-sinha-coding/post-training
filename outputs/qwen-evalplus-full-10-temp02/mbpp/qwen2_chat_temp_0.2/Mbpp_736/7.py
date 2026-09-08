def left_insertion(arr, x):
    # Initialize the index to 0
    i = 0
    # Iterate through the array
    while i < len(arr):
        # If the current element is less than or equal to x, move to the next element
        if arr[i] <= x:
            i += 1
        else:
            # If the current element is greater than x, return the current index
            return i
    # If no element is found greater than x, return the length of the array
    return len(arr)