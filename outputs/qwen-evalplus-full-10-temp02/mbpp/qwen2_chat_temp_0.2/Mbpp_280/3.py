def sequential_search(arr, element):
    """
    This function checks if an element exists in a given array and returns a tuple indicating whether the element is present and its index position.
    
    Parameters:
    arr (list): The array to search through.
    element (int): The element to search for.
    
    Returns:
    tuple: A tuple containing a boolean indicating if the element is present and its index position (or -1 if not found).
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        if value == element:
            return (True, index)
    # If the element is not found, return -1
    return (-1, -1)
