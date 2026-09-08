def dict_filter(dict1, n):
    """
    This function takes in a dictionary and an integer n, and filters the dictionary to only include entries with values greater than or equal to n.
    
    Parameters:
    dict1 (dict): The dictionary to be filtered.
    n (int): The threshold value to filter the dictionary by.
    
    Returns:
    dict: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Using dictionary comprehension to filter the dictionary
    filtered_dict = {key: value for key, value in dict1.items() if value >= n}
    return filtered_dict