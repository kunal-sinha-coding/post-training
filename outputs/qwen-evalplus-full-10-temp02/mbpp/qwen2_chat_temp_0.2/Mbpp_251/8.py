def insert_element(lst, element):
    """
    Insert the element before each element in the list and return the resulting list.
    
    Parameters:
    lst (list): The list of elements.
    element (any): The element to be inserted before each element in the list.
    
    Returns:
    list: A new list with the element inserted before each element in the original list.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for i in lst:
        # Append the element before the current element to the result list
        result.append(element)
        # Append the current element to the result list
        result.append(i)
    # Return the result list
    return result