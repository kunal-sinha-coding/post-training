def check_K(tuples, k):
    """
    Check if the given tuples contain the k or not.
    
    Args:
    tuples (tuple): The tuple to check.
    k (int): The number to check for in the tuples.
    
    Returns:
    bool: True if the k is found in any of the tuples, False otherwise.
    """
    # Iterate through each tuple in the list
    for t in tuples:
        # Check if the k is in the current tuple
        if k in t:
            return True
    # If no k is found in any tuple, return False
    return False