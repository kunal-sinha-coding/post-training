def convert_list_dictionary(list_of_lists, list_of_values, list_of_keys):
    """
    Convert a list of lists into a nested dictionary.
    
    Parameters:
    list_of_lists (list of list): A list of lists to be converted.
    list_of_values (list of int): A list of integer values corresponding to the lists.
    list_of_keys (list of str): A list of string keys corresponding to the lists.
    
    Returns:
    dict: A nested dictionary created from the input lists.
    """
    nested_dict = {}
    for i in range(len(list_of_lists)):
        nested_dict[list_of_keys[i]] = {}
        for j in range(len(list_of_lists[i])):
            nested_dict[list_of_keys[i]][list_of_values[j]] = list_of_lists[i][j]
    return nested_dict
