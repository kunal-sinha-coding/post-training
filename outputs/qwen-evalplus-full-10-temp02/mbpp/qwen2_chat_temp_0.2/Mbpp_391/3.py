def convert_list_dictionary(list1, list2, list3):
    # Initialize an empty list to store the nested dictionaries
    nested_dict_list = []
    
    # Iterate over each list in the input
    for i in range(len(list1)):
        # Create a dictionary for the current list
        nested_dict = {}
        # Iterate over each element in the current list
        for j in range(len(list2)):
            # Add the element to the nested dictionary
            nested_dict[list2[j]] = list3[j]
        # Append the nested dictionary to the list of nested dictionaries
        nested_dict_list.append(nested_dict)
    
    # Return the list of nested dictionaries
    return nested_dict_list