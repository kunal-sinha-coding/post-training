def split_two_parts(lst, L):
    """
    Splits a given list into two parts where the length of the first part is L.
    
    Parameters:
    lst (list): The list to be split.
    L (int): The length of the first part of the resulting list.
    
    Returns:
    tuple: A tuple containing the two resulting lists.
    """
    # Splitting the list into two parts
    part1 = lst[:L]
    part2 = lst[L:]
    return part1, part2
