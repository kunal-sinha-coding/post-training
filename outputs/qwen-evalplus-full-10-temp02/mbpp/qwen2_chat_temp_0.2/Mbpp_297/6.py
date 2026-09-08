def flatten_list(nested_list):
    """
    Flatten a given nested list structure.
    
    Args:
    nested_list (list): A list containing nested lists.
    
    Returns:
    list: A flattened list containing all the elements from the nested lists.
    """
    flattened_list = []
    for item in nested_list:
        if isinstance(item, list):
            flattened_list.extend(flatten_list(item))
        else:
            flattened_list.append(item)
    return flattened_list
