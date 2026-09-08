def count_element_in_list(list_of_lists, element):
    """
    This function counts the number of sublists in a given list that contain a specific element.
    
    Parameters:
    list_of_lists (list of lists): The list of lists to search through.
    element (any): The element to search for within the sublists.
    
    Returns:
    int: The count of sublists containing the specified element.
    """
    count = 0
    for sublist in list_of_lists:
        if element in sublist:
            count += 1
    return count
