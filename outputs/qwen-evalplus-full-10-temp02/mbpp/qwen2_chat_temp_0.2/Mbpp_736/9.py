def left_insertion(arr, x):
    # Initialize the insertion point to 0
    insertion_point = 0
    # Iterate through the array starting from the second element
    for i in range(1, len(arr)):
        # If the current element is greater than the target value, move the insertion point
        if arr[i] > x:
            insertion_point = i
    # Return the insertion point
    return insertion_point