def list_to_float(list_of_lists):
    """
    Convert all possible convertible elements in a list of lists to floats.
    
    Parameters:
    list_of_lists (list of list): A list of lists containing elements that can be converted to floats.
    
    Returns:
    list of float: A new list containing the converted elements.
    """
    # Convert each element in the list of lists to a float
    converted_list = [float(element) for element in list_of_lists]
    return converted_list
