def div_list(list1, list2):
    """
    Divides two lists element-wise.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list containing the element-wise division of list1 by list2.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the elements of both lists
    for i in range(len(list1)):
        # Perform element-wise division and append to the result list
        result.append(list1[i] / list2[i])
    return result