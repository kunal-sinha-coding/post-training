def convert_list_dictionary(list_of_names, list_of_addresses, list_of_scores):
    # Initialize an empty list to store the nested dictionaries
    nested_dict_list = []
    
    # Iterate over each name in the first list
    for name in list_of_names:
        # Create a dictionary for the current name
        name_dict = {}
        # Iterate over each address in the second list
        for address in list_of_addresses:
            # Add the address to the current name dictionary
            name_dict[address] = list_of_scores.pop(0)
        # Append the current name dictionary to the nested dictionary list
        nested_dict_list.append(name_dict)
    
    # Return the nested dictionary list
    return nested_dict_list