def convert_list_dictionary(list_of_names, list_of_adults, list_of_scores):
    # Initialize an empty list to store the nested dictionary
    nested_dict = []
    
    # Iterate over the list of names
    for name in list_of_names:
        # Create a dictionary for the current name
        current_dict = {}
        # Iterate over the list of adults
        for adult in list_of_adults:
            # Add the adult's name as a key to the current dictionary
            current_dict[adult] = list_of_scores[list_of_scores.index(adult)]
        # Append the current dictionary to the nested dictionary
        nested_dict.append(current_dict)
    
    # Return the nested dictionary
    return nested_dict