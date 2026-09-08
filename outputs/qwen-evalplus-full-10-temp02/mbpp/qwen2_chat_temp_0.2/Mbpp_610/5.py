def remove_kth_element(lst, k):
    """
    This function takes a list and an integer k as input and returns a new list with the k'th element removed.
    
    Parameters:
    lst (list): The input list from which the k'th element will be removed.
    k (int): The index of the element to be removed from the list.
    
    Returns:
    list: A new list with the k'th element removed.
    """
    # Check if the k is out of range
    if k < 0 or k >= len(lst):
        return lst
    
    # Create a new list with the k'th element removed
    return lst[:k] + lst[k+1:]
