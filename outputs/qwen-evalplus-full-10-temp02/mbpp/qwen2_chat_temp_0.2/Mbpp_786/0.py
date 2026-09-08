def right_insertion(arr, x):
    # Initialize the insertion point to the last index of the array
    insertion_point = len(arr) - 1
    # Traverse the array from the end to the beginning
    for i in range(len(arr) - 1, -1, -1):
        # If the current element is less than or equal to the target value, move the insertion point to the current index
        if arr[i] <= x:
            insertion_point = i
            break
    # Return the insertion point
    return insertion_point