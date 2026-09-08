def list_split(lst, n):
    """
    Splits a list into every nth element and returns a list of the resulting lists.
    
    Parameters:
    lst (list): The input list to be split.
    n (int): The interval at which to split the list.
    
    Returns:
    list: A list of lists, where each sublist contains every nth element from the original list.
    """
    # Initialize an empty list to store the resulting lists
    result = []
    # Iterate over the list with a step of n
    for i in range(0, len(lst), n):
        # Append the sublist to the result list
        result.append(lst[i:i+n])
    return result
