def list_split(lst, n):
    """
    Splits a list into sublists of a specified length.
    
    Parameters:
    lst (list): The list to be split.
    n (int): The length of each sublist.
    
    Returns:
    list: A list of sublists.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the list, taking every nth element
    for i in range(0, len(lst), n):
        # Append the sublist to the result list
        result.append(lst[i:i+n])
    return result
