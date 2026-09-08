def merge_dictionaries_three(dict1, dict2, dict3):
    # Create a new dictionary to store the merged results
    merged_dict = {}
    
    # Iterate over the keys of the first dictionary
    for key in dict1:
        # If the key is already in the merged dictionary, append the value
        if key in merged_dict:
            merged_dict[key] += dict1[key]
        # Otherwise, add the key-value pair to the merged dictionary
        else:
            merged_dict[key] = dict1[key]
    
    # Iterate over the keys of the second dictionary
    for key in dict2:
        # If the key is already in the merged dictionary, append the value
        if key in merged_dict:
            merged_dict[key] += dict2[key]
        # Otherwise, add the key-value pair to the merged dictionary
        else:
            merged_dict[key] = dict2[key]
    
    # Iterate over the keys of the third dictionary
    for key in dict3:
        # If the key is already in the merged dictionary, append the value
        if key in merged_dict:
            merged_dict[key] += dict3[key]
        # Otherwise, add the key-value pair to the merged dictionary
        else:
            merged_dict[key] = dict3[key]
    
    # Return the merged dictionary
    return merged_dict