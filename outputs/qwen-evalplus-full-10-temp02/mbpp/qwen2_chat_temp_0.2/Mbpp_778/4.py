def pack_consecutive_duplicates(lst):
    """
    Pack consecutive duplicates of a given list elements into sublists.
    
    Args:
    lst (list): The input list of elements.
    
    Returns:
    list: A list of sublists, where each sublist contains consecutive duplicates of the input list.
    """
    result = []
    for i in range(len(lst) - 1):
        if lst[i] == lst[i + 1]:
            result.append([lst[i], lst[i + 1]])
        else:
            result.append([lst[i]])
    return result
