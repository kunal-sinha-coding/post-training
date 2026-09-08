def list_split(lst, n):
    """
    Splits a list into sublists of a specified length.
    
    Parameters:
    lst (list): The original list to be split.
    n (int): The length of each sublist.
    
    Returns:
    list: A list of sublists, each containing 'n' elements from the original list.
    """
    # Initialize an empty list to store the sublists
    sublists = []
    # Iterate over the original list, taking every 'n' elements at a time
    for i in range(0, len(lst), n):
        # Append the sublist to the list of sublists
        sublists.append(lst[i:i+n])
    return sublists