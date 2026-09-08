def dict_filter(dictionary, n):
    """
    Filters a dictionary to include only entries with values greater than or equal to n.
    
    Args:
    dictionary (dict): The dictionary to filter.
    n (int): The minimum value to filter the dictionary by.
    
    Returns:
    dict: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Filter the dictionary to include only entries with values greater than or equal to n
    filtered_dict = {key: value for key, value in dictionary.items() if value >= n}
    return filtered_dict