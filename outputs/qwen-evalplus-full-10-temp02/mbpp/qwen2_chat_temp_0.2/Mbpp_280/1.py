def sequential_search(arr, element):
    """
    This function checks if the given element is present in the array and returns a tuple
    containing a boolean indicating if the element is found and the index position of the element
    (or -1 if the element is not found).
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        if value == element:
            # Return the boolean indicating the presence and the index
            return (True, index)
    # Return -1 if the element is not found
    return (-1, -1)
