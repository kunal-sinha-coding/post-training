def consecutive_duplicates(lst):
    """
    Remove consecutive duplicates from a given list.
    
    Parameters:
    lst (list): The input list from which duplicates need to be removed.
    
    Returns:
    list: A new list with duplicates removed.
    """
    # Initialize an empty list to store unique elements
    unique_lst = []
    
    # Iterate through each element in the input list
    for element in lst:
        # If the current element is not the same as the last element in the unique list
        if element != unique_lst[-1]:
            # Append the current element to the unique list
            unique_lst.append(element)
    
    return unique_lst
