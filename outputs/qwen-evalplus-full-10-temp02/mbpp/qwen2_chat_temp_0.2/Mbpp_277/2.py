def dict_filter(dict1, n):
    """
    Filters a dictionary to include only entries with values greater than or equal to n.
    
    Parameters:
    dict1 (dict): The dictionary to be filtered.
    n (int): The threshold value.
    
    Returns:
    dict: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Filter the dictionary to include only entries with values greater than or equal to n
    filtered_dict = {key: value for key, value in dict1.items() if value >= n}
    return filtered_dict