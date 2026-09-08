def convert_list_dictionary(list_of_lists, list_of_dicts):
    """
    Convert a list of lists into a nested dictionary.
    
    Parameters:
    list_of_lists (list of list): A list containing sublists.
    list_of_dicts (list of dict): A list containing dictionaries.
    
    Returns:
    list of dict: A list of nested dictionaries.
    """
    # Initialize an empty list to store the result
    result = []
    
    # Iterate over each sublist in the list of lists
    for sublist in list_of_lists:
        # Create a new dictionary for the current sublist
        current_dict = {}
        # Iterate over each dictionary in the list of dicts
        for dict_item in list_of_dicts:
            # Add the key-value pair from the current sublist to the current dictionary
            current_dict.update(dict_item)
        # Append the current dictionary to the result list
        result.append(current_dict)
    
    return result