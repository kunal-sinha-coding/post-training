def extract_singly(lst):
    """
    Flatten the list of lists into a single set of numbers.
    
    Args:
    lst (list of lists): The list of lists to flatten.
    
    Returns:
    set: A set of numbers from the flattened list.
    """
    # Flatten the list of lists
    flat_list = [item for sublist in lst for item in sublist]
    # Convert the list to a set to remove duplicates
    return set(flat_list)
