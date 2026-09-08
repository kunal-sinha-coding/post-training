def convert_list_dictionary(list1, list2, list3):
    # Initialize an empty list to store the nested dictionaries
    nested_dict_list = []
    
    # Iterate over each list in the input
    for i in range(len(list1)):
        # Create a dictionary for the current list
        current_dict = {}
        # Iterate over each element in the current list
        for j in range(len(list2)):
            # Add the element to the current dictionary
            current_dict[list2[j]] = list3[j]
        # Append the current dictionary to the nested dictionary list
        nested_dict_list.append(current_dict)
    
    # Return the nested dictionary list
    return nested_dict_list