def right_insertion(arr, x):
    # Initialize the insertion point to the last index of the array
    insertion_point = len(arr) - 1
    
    # Iterate from the last index of the array to the first index
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is less than the target value
        if arr[i] < x:
            # If it is, move the insertion point to the current index
            insertion_point = i
            break
    
    # Return the insertion point
    return insertion_point