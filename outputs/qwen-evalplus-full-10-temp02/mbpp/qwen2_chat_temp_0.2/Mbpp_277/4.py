def dict_filter(dictionary, n):
    """
    This function takes a dictionary and an integer n as input and returns a new dictionary containing only the entries with values greater than or equal to n.
    
    :param dictionary: The input dictionary to filter.
    :param n: The threshold value to filter the dictionary by.
    :return: A new dictionary containing only the entries with values greater than or equal to n.
    """
    # Filter the dictionary to include only entries with values greater than or equal to n
    filtered_dict = {key: value for key, value in dictionary.items() if value >= n}
    return filtered_dict