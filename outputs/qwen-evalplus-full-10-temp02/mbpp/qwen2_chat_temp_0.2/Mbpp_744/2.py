def check_none(test_tuple):
    """
    Check if the given tuple contains any none value.
    
    Args:
    test_tuple (tuple): The tuple to check.
    
    Returns:
    bool: True if the tuple contains any none value, False otherwise.
    """
    # Check if any element in the tuple is None
    return any(value is None for value in test_tuple)
