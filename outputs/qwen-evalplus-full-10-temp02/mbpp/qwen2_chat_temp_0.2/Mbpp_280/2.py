def sequential_search(arr, element):
    """
    This function checks if the element is present in the array and returns a tuple containing a boolean indicating if the element is found and the index position of the element (or -1 if the element is not found).
    
    Parameters:
    arr (list): The list in which to search for the element.
    element (int): The element to search for in the list.
    
    Returns:
    tuple: A tuple containing a boolean indicating if the element is found and the index position of the element (or -1 if the element is not found).
    """
    # Iterate through the list to find the element
    for index, value in enumerate(arr):
        if value == element:
            return (True, index)
    # If the element is not found, return (-1, -1)
    return (-1, -1)