def get_equal(tuples_list):
    """
    Check if all tuples in the given list have the same length.
    
    Args:
    tuples_list (list of tuples): A list containing tuples to be checked.
    
    Returns:
    bool: True if all tuples have the same length, False otherwise.
    """
    # Check if all tuples have the same length
    if all(len(tup) == len(tup_list[0]) for tup in tuples_list):
        return True
    else:
        return False