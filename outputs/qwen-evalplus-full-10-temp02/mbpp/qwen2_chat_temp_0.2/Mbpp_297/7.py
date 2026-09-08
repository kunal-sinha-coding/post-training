def flatten_list(nested_list):
    """
    Flatten a given nested list structure.
    
    Args:
    nested_list (list): A list containing nested lists.
    
    Returns:
    list: A flattened list containing all the elements from the nested lists.
    """
    flat_list = []
    for element in nested_list:
        if isinstance(element, list):
            flat_list.extend(flatten_list(element))
        else:
            flat_list.append(element)
    return flat_list
