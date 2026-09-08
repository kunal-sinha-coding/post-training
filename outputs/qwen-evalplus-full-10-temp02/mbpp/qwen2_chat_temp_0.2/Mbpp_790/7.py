def even_position(lst):
    """
    Check if every even index contains even numbers of a given list.
    
    Args:
    lst (list): The input list of integers.
    
    Returns:
    bool: True if every even index contains even numbers, False otherwise.
    """
    for i in range(0, len(lst), 2):
        if lst[i] % 2 != 0:
            return False
    return True