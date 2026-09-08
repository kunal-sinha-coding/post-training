def sub_list(list1, list2):
    """
    Subtract two lists element-wise.
    
    Args:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list containing the element-wise difference between list1 and list2.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the elements of both lists
    for i in range(len(list1)):
        # Subtract the corresponding elements from list1 and list2
        result.append(list1[i] - list2[i])
    # Return the result list
    return result