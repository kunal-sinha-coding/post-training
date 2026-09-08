def right_insertion(arr, x):
    """
    This function takes a sorted array and a value as input and returns the index of the right insertion point.
    
    Parameters:
    arr (list): The sorted array.
    x (int): The value to insert into the array.
    
    Returns:
    int: The index of the right insertion point.
    """
    # Initialize the index to the length of the array
    index = len(arr)
    
    # Traverse the array from the end to the beginning
    while index > 0 and arr[index - 1] < x:
        # Move the index one position to the left
        index -= 1
    
    # Return the index where the value should be inserted
    return index