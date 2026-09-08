def insert_element(lst, element):
    """
    Insert the given element before each element in the list and return the resulting list.
    
    Parameters:
    lst (list): The list to which the element will be inserted.
    element (any): The element to be inserted before each element in the list.
    
    Returns:
    list: A new list with the element inserted before each element in the original list.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over each element in the original list
    for i in lst:
        # Append the element before the current element to the result list
        result.append(element)
        # Append the current element to the result list
        result.append(i)
    return result