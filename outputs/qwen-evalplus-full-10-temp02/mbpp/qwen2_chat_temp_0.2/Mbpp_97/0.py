def frequency_lists(flattened_list):
    # Flatten the list of lists
    flat_list = [item for sublist in flattened_list for item in sublist]
    # Create a dictionary to store the frequency of each element
    frequency_dict = {}
    # Iterate over the flattened list and count the frequency of each element
    for item in flat_list:
        if item in frequency_dict:
            frequency_dict[item] += 1
        else:
            frequency_dict[item] = 1
    return frequency_dict