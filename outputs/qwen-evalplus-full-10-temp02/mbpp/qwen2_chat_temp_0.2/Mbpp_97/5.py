def frequency_lists(flattened_list):
    """
    This function takes a flattened list of lists and returns a dictionary where each key is an element from the flattened list,
    and the value is the frequency of that element in the flattened list.
    
    :param flattened_list: List of lists to be flattened and analyzed.
    :return: Dictionary with elements as keys and their frequencies as values.
    """
    frequency = {}
    for sublist in flattened_list:
        for element in sublist:
            if element in frequency:
                frequency[element] += 1
            else:
                frequency[element] = 1
    return frequency