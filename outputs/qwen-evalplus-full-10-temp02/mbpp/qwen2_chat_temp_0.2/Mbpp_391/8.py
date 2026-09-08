def convert_list_dictionary(list1, list2, list3):
    # Initialize an empty list to store the nested dictionaries
    nested_dict_list = []
    
    # Iterate over the first list
    for item in list1:
        # Create a new dictionary for the current item
        nested_dict = {}
        # Iterate over the second list
        for sub_item in list2:
            # Add the sub-item to the nested dictionary
            nested_dict[sub_item] = list3[list3.index(sub_item)]
        # Append the nested dictionary to the list
        nested_dict_list.append(nested_dict)
    
    # Return the list of nested dictionaries
    return nested_dict_list