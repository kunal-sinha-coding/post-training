def list_to_float(list_of_lists):
    """
    Convert all possible convertible elements in a list of lists to floats.
    
    Args:
    list_of_lists (list of list of str): A list of lists containing strings.
    
    Returns:
    list of list of float: A new list of lists with all convertible elements converted to floats.
    """
    # Convert each string in the list to a float
    converted_list = [[float(element) for element in sublist] for sublist in list_of_lists]
    return converted_list