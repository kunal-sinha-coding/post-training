def pack_consecutive_duplicates(lst):
    """
    Pack consecutive duplicates of a given list elements into sublists.
    
    Args:
    lst (list): The input list of elements.
    
    Returns:
    list: A list of sublists, where each sublist contains consecutive duplicates of the input list.
    """
    result = []
    current = lst[0]
    for element in lst[1:]:
        if element == current:
            current += 1
        else:
            result.append([current])
            current = element
    result.append([current])  # Add the last element as a sublist
    return result
