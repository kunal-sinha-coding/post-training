def check_Consecutive(lst):
    """
    Check if the given list contains consecutive numbers or not.
    
    Args:
    lst (list): The list to check.
    
    Returns:
    bool: True if the list contains consecutive numbers, False otherwise.
    """
    # Check if the list is empty
    if not lst:
        return False
    
    # Iterate through the list and check for consecutive numbers
    for i in range(len(lst) - 1):
        if lst[i] + 1 == lst[i + 1]:
            return True
    
    # If no consecutive numbers are found, return False
    return False