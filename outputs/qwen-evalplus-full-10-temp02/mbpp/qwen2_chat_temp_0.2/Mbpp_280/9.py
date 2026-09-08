def sequential_search(arr, element):
    """
    This function checks if an element exists in the given array and returns a tuple
    containing a boolean indicating if the element is found and the index position of the element.
    If the element is not found, it returns (-1, -1).
    
    Parameters:
    arr (list): The array to search through.
    element (int): The element to search for.
    
    Returns:
    tuple: A tuple containing a boolean indicating if the element is found and the index position of the element.
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        if value == element:
            return (True, index)
    # If the element is not found, return (-1, -1)
    return (-1, -1)
