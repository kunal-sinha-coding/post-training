def check_none(test_tup):
    """
    Check if the given tuple has any none value or not.
    
    Args:
    test_tup (tuple): The tuple to check.
    
    Returns:
    bool: True if the tuple contains any none value, False otherwise.
    """
    # Check if any element in the tuple is None
    return any(test_tup is None for test_tup in test_tup)