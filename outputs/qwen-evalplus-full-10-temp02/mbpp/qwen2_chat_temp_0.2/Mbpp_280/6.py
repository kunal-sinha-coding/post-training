def sequential_search(arr, element):
    """
    This function checks if an element exists in an array and returns a tuple indicating
    whether the element is present and its index position. If the element is not found,
    it returns (-1, -1).
    
    Parameters:
    arr (list): The array to search through.
    element (int): The element to search for.
    
    Returns:
    tuple: A tuple containing a boolean indicating if the element is found and its index position,
           or (-1, -1) if the element is not found.
    """
    for index, value in enumerate(arr):
        if value == element:
            return (True, index)
    return (-1, -1)
