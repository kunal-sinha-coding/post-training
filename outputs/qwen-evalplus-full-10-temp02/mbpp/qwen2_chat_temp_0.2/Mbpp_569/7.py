def sort_sublists(list_of_lists):
    """
    Sort each sublist of strings in a given list of lists.
    
    Args:
    list_of_lists (list of list of str): A list of lists where each sublist contains strings.
    
    Returns:
    list of list of str: A new list where each sublist has been sorted.
    """
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Sort the sublist of strings
        sublist.sort()
    return list_of_lists
