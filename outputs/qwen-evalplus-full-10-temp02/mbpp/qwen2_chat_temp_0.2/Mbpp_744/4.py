def check_none(test_tuple):
    """
    Check if the given tuple has any none value or not.
    
    Args:
    test_tuple (tuple): The tuple to check.
    
    Returns:
    bool: True if the tuple contains any none value, False otherwise.
    """
    # Check if any element in the tuple is None
    return any(test_tuple is None for _ in test_tuple)
