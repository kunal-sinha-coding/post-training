def count_element_in_list(list_of_lists, element):
    """
    Counts the number of sublists containing a particular element.
    
    Parameters:
    list_of_lists (list of lists): The list of lists to search through.
    element (any): The element to count within the sublists.
    
    Returns:
    int: The count of sublists containing the specified element.
    """
    count = 0
    for sublist in list_of_lists:
        if element in sublist:
            count += 1
    return count
