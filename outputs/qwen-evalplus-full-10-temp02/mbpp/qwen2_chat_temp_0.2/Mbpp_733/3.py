def find_first_occurrence(arr, target):
    """
    Find the index of the first occurrence of a given number in a sorted array.
    
    Parameters:
    arr (list): The sorted array in which to search for the target.
    target (int): The number to search for in the array.
    
    Returns:
    int: The index of the first occurrence of the target, or -1 if not found.
    """
    # Initialize the index to -1
    index = -1
    
    # Iterate through the array to find the target
    for i in range(len(arr)):
        # If the current element matches the target, update the index
        if arr[i] == target:
            index = i
    
    # Return the index of the target, or -1 if not found
    return index