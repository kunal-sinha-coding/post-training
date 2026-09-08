def sequential_search(arr, element):
    """
    This function checks if the given element is present in the array and returns a tuple
    containing a boolean indicating whether the element is found and the index position of the element
    (or -1 if the element is not found).
    
    :param arr: List of elements to search through.
    :param element: The element to search for.
    :return: A tuple (found, index) where found is a boolean indicating if the element is found,
             and index is the index position of the element (or -1 if not found).
    """
    found = False
    index = -1
    for i in range(len(arr)):
        if arr[i] == element:
            found = True
            index = i
    return (found, index)