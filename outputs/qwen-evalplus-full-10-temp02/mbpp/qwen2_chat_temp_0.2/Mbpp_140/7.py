def extract_singly(lst):
    """
    Flatten a list of lists into a single set of numbers.
    
    Args:
    lst (list of list): The list of lists to be flattened.
    
    Returns:
    set: A set of numbers from the flattened list.
    """
    # Use set comprehension to flatten the list
    return set(item for sublist in lst for item in sublist)
