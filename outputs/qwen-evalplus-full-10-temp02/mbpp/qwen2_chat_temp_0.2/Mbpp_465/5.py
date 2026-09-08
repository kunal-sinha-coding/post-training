def drop_empty(input_dict):
    """
    Drop empty items from a given dictionary.
    
    Parameters:
    input_dict (dict): The dictionary from which empty items will be dropped.
    
    Returns:
    dict: A new dictionary with all empty items removed.
    """
    # Use a dictionary comprehension to filter out empty values
    return {key: value for key, value in input_dict.items() if value}
