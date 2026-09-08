def merge_dictionaries_three(dict1, dict2, dict3):
    """
    Merge three dictionaries into a single dictionary.
    
    Parameters:
    dict1 (dict): The first dictionary.
    dict2 (dict): The second dictionary.
    dict3 (dict): The third dictionary.
    
    Returns:
    dict: A single dictionary containing all key-value pairs from the three input dictionaries.
    """
    # Create a new dictionary to store the merged results
    merged_dict = {}
    
    # Iterate over each key-value pair in the first dictionary
    for key, value in dict1.items():
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = value
        # If the key is already in the merged dictionary, update its value
        else:
            merged_dict[key] = value
    
    # Iterate over each key-value pair in the second dictionary
    for key, value in dict2.items():
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = value
        # If the key is already in the merged dictionary, update its value
        else:
            merged_dict[key] = value
    
    # Iterate over each key-value pair in the third dictionary
    for key, value in dict3.items():
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = value
        # If the key is already in the merged dictionary, update its value
        else:
            merged_dict[key] = value
    
    return merged_dict