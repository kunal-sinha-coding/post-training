def right_insertion(arr, x):
    """
    Locate the right insertion point for a specified value in sorted order.
    
    Parameters:
    arr (list): The sorted list of elements.
    x (int): The value to be inserted.
    
    Returns:
    int: The index where the value should be inserted.
    """
    # Initialize the insertion point to the last index of the array
    insertion_point = len(arr) - 1
    
    # Iterate from the last index to the first index
    for i in range(len(arr) - 1, -1, -1):
        # Check if the current element is less than the target value
        if arr[i] < x:
            # If it is, move the insertion point one position to the right
            insertion_point -= 1
    
    # Return the insertion point
    return insertion_point