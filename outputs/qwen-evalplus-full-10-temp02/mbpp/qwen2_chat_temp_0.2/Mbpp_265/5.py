def list_split(lst, n):
    """
    Splits a list into sublists of a specified length.
    
    Parameters:
    lst (list): The original list to be split.
    n (int): The length of each sublist to be created.
    
    Returns:
    list: A list of sublists, each containing 'n' elements from the original list.
    """
    # Initialize an empty list to store the resulting sublists
    result = []
    # Iterate over the original list in steps of 'n'
    for i in range(0, len(lst), n):
        # Append a sublist of 'n' elements from the original list to the result list
        result.append(lst[i:i+n])
    return result
