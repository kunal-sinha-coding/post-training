def sequential_search(arr, element):
    """
    This function checks if an element exists in a given array and returns a tuple containing a boolean indicating the presence of the element and its index position (or -1 if the element is not found).
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        if value == element:
            # Return a tuple with True and the index position
            return (True, index)
    # Return a tuple with False and -1 if the element is not found
    return (False, -1)