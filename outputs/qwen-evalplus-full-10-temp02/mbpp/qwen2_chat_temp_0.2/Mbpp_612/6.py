def merge(list_of_lists):
    """
    Merge a list of lists, where each sublist has two elements, into a list of two lists.
    
    Parameters:
    list_of_lists (list of list): A list of lists, where each sublist has two elements.
    
    Returns:
    list of list: A list of two lists where the first list has the first element of each sublist and the second one has the second.
    """
    # Initialize an empty list to store the merged result
    merged_list = []
    
    # Iterate over each sublist in the input list
    for sublist in list_of_lists:
        # Append the first element of the sublist to the merged list
        merged_list.append(sublist[0])
        # Append the second element of the sublist to the merged list
        merged_list.append(sublist[1])
    
    return merged_list
