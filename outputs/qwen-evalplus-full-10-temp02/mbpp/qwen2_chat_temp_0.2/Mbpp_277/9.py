def dict_filter(input_dict, n):
    """
    Filters a dictionary to include only entries with values greater than or equal to n.
    
    Parameters:
    input_dict (dict): The dictionary to be filtered.
    n (int): The threshold value to filter the dictionary by.
    
    Returns:
    dict: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Using dictionary comprehension to filter the dictionary
    filtered_dict = {key: value for key, value in input_dict.items() if value >= n}
    return filtered_dict