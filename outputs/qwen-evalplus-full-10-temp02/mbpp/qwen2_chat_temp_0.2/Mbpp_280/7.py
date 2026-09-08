def sequential_search(arr, element):
    """
    This function checks if an element exists in the given array and returns a tuple containing a boolean indicating the presence of the element and the index position of the element (or -1 if the element is not found).
    """
    # Iterate through the array to find the element
    for index, value in enumerate(arr):
        # Check if the current element matches the target element
        if value == element:
            # Return a tuple with True and the index of the element
            return (True, index)
    # Return a tuple with False and -1 if the element is not found
    return (False, -1)