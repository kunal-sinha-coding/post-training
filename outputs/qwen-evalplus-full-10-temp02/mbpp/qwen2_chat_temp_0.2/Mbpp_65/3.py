def recursive_list_sum(lst):
    """
    Flatten a list and sum all of its elements.
    
    Args:
    lst (list): The list to be flattened and summed.
    
    Returns:
    int: The sum of all elements in the flattened list.
    """
    # Base case: if the list is empty, return 0
    if not lst:
        return 0
    # Recursive case: sum the first element and the result of the flatten operation on the rest of the list
    return lst[0] + recursive_list_sum(lst[1:])
