def drop_empty(dictionary):
    """
    Drop empty items from a given dictionary.
    
    Args:
    dictionary (dict): The dictionary from which empty items will be dropped.
    
    Returns:
    dict: A new dictionary with all empty items removed.
    """
    # Use dictionary comprehension to filter out empty items
    return {key: value for key, value in dictionary.items() if value}
