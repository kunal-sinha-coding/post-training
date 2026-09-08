def count_element_in_list(lst, element):
    """
    Count the number of sublists containing a particular element.
    
    Parameters:
    lst (list of lists): The list of lists to search through.
    element (int): The element to count sublists containing.
    
    Returns:
    int: The count of sublists containing the element.
    """
    count = 0
    for sublist in lst:
        if element in sublist:
            count += 1
    return count
