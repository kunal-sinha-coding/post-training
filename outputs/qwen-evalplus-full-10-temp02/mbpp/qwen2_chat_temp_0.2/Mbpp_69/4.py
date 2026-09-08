def is_sublist(lst, sublst):
    """
    Check if the list contains the given sublist or not.
    
    Args:
    lst (list): The list to search within.
    sublst (list): The sublist to search for.
    
    Returns:
    bool: True if the sublist is found in the list, False otherwise.
    """
    # Check if the sublist is empty
    if not sublst:
        return True
    
    # Iterate through the list and check if the sublist is found
    for i in range(len(lst)):
        # Check if the current element matches the first element of the sublist
        if lst[i] == sublst[0]:
            # Check if the rest of the sublist matches the rest of the current element
            if lst[i:i+len(sublst)] == sublst:
                return True
    return False