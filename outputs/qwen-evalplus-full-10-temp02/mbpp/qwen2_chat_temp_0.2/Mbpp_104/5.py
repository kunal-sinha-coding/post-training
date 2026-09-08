def sort_sublists(list_of_lists):
    """
    Sort each sublist of strings in a given list of lists.
    
    Args:
    list_of_lists (list of list of str): The input list of lists.
    
    Returns:
    list of list of str: A new list of lists with each sublist sorted.
    """
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Sort the sublist using the sorted() function
        sublist.sort()
    # Return the modified list of lists
    return list_of_lists
