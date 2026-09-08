def find_first_occurrence(arr, target):
    """
    Find the index of the first occurrence of a given number in a sorted array.
    
    Parameters:
    arr (list): The sorted array to search through.
    target (int): The number to find in the array.
    
    Returns:
    int: The index of the first occurrence of the target number, or -1 if not found.
    """
    # Initialize the index to -1
    index = -1
    
    # Iterate through the array
    for i in range(len(arr)):
        # Check if the current element is equal to the target
        if arr[i] == target:
            # Update the index if the current element is the first occurrence
            index = i
    
    # Return the index of the first occurrence, or -1 if not found
    return index