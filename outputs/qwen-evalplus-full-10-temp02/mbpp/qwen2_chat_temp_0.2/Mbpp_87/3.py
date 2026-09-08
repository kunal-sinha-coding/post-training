def merge_dictionaries_three(dict1, dict2, dict3):
    # Create a new dictionary to store the merged results
    merged_dict = {}
    
    # Iterate over the keys of the first dictionary
    for key in dict1:
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = dict1[key]
        else:
            # If the key is already in the merged dictionary, update its value
            merged_dict[key] = dict1[key]
    
    # Iterate over the keys of the second dictionary
    for key in dict2:
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = dict2[key]
        else:
            # If the key is already in the merged dictionary, update its value
            merged_dict[key] = dict2[key]
    
    # Iterate over the keys of the third dictionary
    for key in dict3:
        # If the key is not already in the merged dictionary, add it
        if key not in merged_dict:
            merged_dict[key] = dict3[key]
        else:
            # If the key is already in the merged dictionary, update its value
            merged_dict[key] = dict3[key]
    
    return merged_dict