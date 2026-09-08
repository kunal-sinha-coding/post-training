def flatten_list(nested_list):
    """
    Flatten a given nested list structure.
    
    Args:
    nested_list (list): A list containing nested lists.
    
    Returns:
    list: A flattened list containing all elements from the nested lists.
    """
    flat_list = []
    for item in nested_list:
        if isinstance(item, list):
            flat_list.extend(flatten_list(item))
        else:
            flat_list.append(item)
    return flat_list
