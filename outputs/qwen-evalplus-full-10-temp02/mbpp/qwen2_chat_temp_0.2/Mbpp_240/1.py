def replace_list(list1, list2):
    """
    Replace the last element of the first list with the elements of the second list.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: The modified list with the last element replaced by the second list.
    """
    # Replace the last element of list1 with the elements of list2
    list1[-1] = list2
    return list1
