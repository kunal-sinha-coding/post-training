def sequential_search(arr, element):
    """
    This function checks if an element exists in an array and returns a tuple containing a boolean indicating the presence of the element and the index position of the element (or -1 if the element is not found).
    
    Parameters:
    arr (list): The array in which to search for the element.
    element (int): The element to search for in the array.
    
    Returns:
    tuple: A tuple containing a boolean indicating if the element is in the array and the index position of the element (or -1 if the element is not found).
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        if value == element:
            # Return the boolean and the index position
            return (True, index)
    # Return False if the element is not found
    return (False, -1)