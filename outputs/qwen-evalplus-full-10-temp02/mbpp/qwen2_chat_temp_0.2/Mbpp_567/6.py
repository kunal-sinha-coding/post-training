def issort_list(lst):
    """
    Check if the list is sorted in ascending order.
    
    Args:
    lst (list): The list to check.
    
    Returns:
    bool: True if the list is sorted in ascending order, False otherwise.
    """
    for i in range(1, len(lst)):
        if lst[i] < lst[i - 1]:
            return False
    return True