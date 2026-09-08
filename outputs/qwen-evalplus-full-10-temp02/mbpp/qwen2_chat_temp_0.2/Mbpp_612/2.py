def merge(list_of_lists):
    """
    Merge a list of lists, where each sublist contains two elements, into a new list of two lists.
    
    Parameters:
    list_of_lists (list of list): A list of lists, where each sublist contains two elements.
    
    Returns:
    list of list: A new list of two lists where the first list has the first element of each sublist and the second one has the second.
    """
    merged_list = []
    for sublist in list_of_lists:
        merged_list.append(sublist[0])
        merged_list.append(sublist[1])
    return merged_list