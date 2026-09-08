def list_to_float(list_of_lists):
    """
    Convert all possible convertible elements in a list of lists to floats.
    
    Args:
    list_of_lists (list of list): A list of lists containing elements that can be converted to floats.
    
    Returns:
    list of float: A list of floats with all elements from the input list of lists converted to floats.
    """
    # Convert each element in the list of lists to a float
    result = [float(element) for element in list_of_lists]
    return result
