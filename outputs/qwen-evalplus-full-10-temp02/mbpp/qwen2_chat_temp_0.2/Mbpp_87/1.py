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
    
    # Iterate over the keys of the first dictionary
    for key in dict1:
        # If the key is already in the merged dictionary, append the value from the second dictionary
        if key in merged_dict:
            merged_dict[key] += dict2[key]
        # If the key is not in the merged dictionary, add it with the value from the third dictionary
        else:
            merged_dict[key] = dict3[key]
    
    return merged_dict