def split_two_parts(lst, L):
    """
    Splits the given list into two parts where the length of the first part is L.
    
    Parameters:
    lst (list): The list to be split.
    L (int): The length of the first part of the resulting list.
    
    Returns:
    tuple: A tuple containing two lists, the first part of the original list is L, and the second part is the rest of the list.
    """
    # Splitting the list into two parts
    first_part = lst[:L]
    second_part = lst[L:]
    return first_part, second_part
