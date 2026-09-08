def extract_singly(lst):
    """
    Flatten a list of lists into a single set of numbers.
    
    Args:
    lst (list of list): The list of lists to be flattened.
    
    Returns:
    set: A set of numbers from the flattened list.
    """
    # Flatten the list of lists
    flat_list = [item for sublist in lst for item in sublist]
    # Convert the list to a set to remove duplicates
    unique_numbers = set(flat_list)
    return unique_numbers
