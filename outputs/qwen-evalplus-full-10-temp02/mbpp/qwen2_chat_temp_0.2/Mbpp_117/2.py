def list_to_float(list_of_lists):
    """
    Convert all possible convertible elements in a list of lists to floats.
    
    Args:
    list_of_lists (list of list): A list of lists containing elements that can be converted to floats.
    
    Returns:
    list of float: A list of floats converted from the input list of lists.
    """
    # Convert each element in the list of lists to a float
    converted_list = [float(element) for element in list_of_lists]
    return converted_list
