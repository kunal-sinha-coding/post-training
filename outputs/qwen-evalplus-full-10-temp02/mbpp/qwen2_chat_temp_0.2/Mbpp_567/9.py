def issort_list(lst):
    """
    Check if a specified list is sorted or not.
    
    Args:
    lst (list): The list to check.
    
    Returns:
    bool: True if the list is sorted, False otherwise.
    """
    # Iterate through the list and compare each element with the next one
    for i in range(len(lst) - 1):
        if lst[i] > lst[i + 1]:
            return False
    return True