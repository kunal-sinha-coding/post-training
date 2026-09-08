def list_split(lst, n):
    """
    Splits a list into sublists of a specified length.
    
    Parameters:
    lst (list): The list to be split.
    n (int): The length of each sublist.
    
    Returns:
    list: A list of sublists of the specified length.
    """
    # Initialize an empty list to store the resulting sublists
    result = []
    # Iterate over the list in steps of n
    for i in range(0, len(lst), n):
        # Append a sublist of the current length to the result list
        result.append(lst[i:i+n])
    return result
