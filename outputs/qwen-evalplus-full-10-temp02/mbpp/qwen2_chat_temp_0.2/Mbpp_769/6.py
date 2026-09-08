def Diff(list1, list2):
    """
    This function takes two lists as input and returns a new list containing the elements that are in list1 but not in list2.
    
    Parameters:
    list1 (list): The first list.
    list2 (list): The second list.
    
    Returns:
    list: A new list containing elements that are in list1 but not in list2.
    """
    # Using list comprehension to filter out elements in list1 that are also in list2
    return [x for x in list1 if x not in list2]
