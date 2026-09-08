def dict_filter(dictionary, n):
    """
    This function takes a dictionary and an integer n as input. It filters the dictionary to include only entries with values greater than or equal to n.
    
    Parameters:
    dictionary (dict): The dictionary to be filtered.
    n (int): The threshold value.
    
    Returns:
    dict: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Using dictionary comprehension to filter the dictionary
    filtered_dict = {key: value for key, value in dictionary.items() if value >= n}
    return filtered_dict