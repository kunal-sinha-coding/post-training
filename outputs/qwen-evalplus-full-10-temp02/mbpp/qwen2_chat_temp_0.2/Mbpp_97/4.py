def frequency_lists(flattened_list):
    # Initialize an empty dictionary to store the frequency of each element
    frequency_dict = {}
    
    # Iterate through each sublist in the flattened list
    for sublist in flattened_list:
        # Iterate through each element in the sublist
        for element in sublist:
            # If the element is already in the dictionary, increment its count
            if element in frequency_dict:
                frequency_dict[element] += 1
            # If the element is not in the dictionary, add it with a count of 1
            else:
                frequency_dict[element] = 1
    
    # Return the dictionary containing the frequency of each element
    return frequency_dict