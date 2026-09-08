def extract_singly(lst):
    """
    Flatten a list of lists into a single set of numbers.
    
    Parameters:
    lst (list of lists): The list of lists to be flattened.
    
    Returns:
    set: A set containing all the numbers from the flattened list.
    """
    # Flatten the list of lists
    flat_list = [item for sublist in lst for item in sublist]
    # Convert the list to a set
    return set(flat_list)
