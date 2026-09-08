def sort_sublists(list_of_lists):
    """
    Sort each sublist of strings in a given list of lists.
    
    Parameters:
    list_of_lists (list of list of str): The input list of lists to be sorted.
    
    Returns:
    list of list of str: A new list of lists with each sublist sorted.
    """
    # Iterate through each sublist in the input list
    for sublist in list_of_lists:
        # Sort the sublist of strings
        sublist.sort()
    return list_of_lists
