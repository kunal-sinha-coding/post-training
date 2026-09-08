def insert_element(lst, element):
    """
    Insert a given element before each element in the provided list.
    
    Parameters:
    lst (list): The list of elements to be modified.
    element (any): The element to be inserted before each element in the list.
    
    Returns:
    list: A new list with the element inserted before each element in the original list.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate through each element in the input list
    for i in lst:
        # Append the element before the current element
        result.append(element)
        # Append the current element to the result list
        result.append(i)
    # Return the modified list
    return result