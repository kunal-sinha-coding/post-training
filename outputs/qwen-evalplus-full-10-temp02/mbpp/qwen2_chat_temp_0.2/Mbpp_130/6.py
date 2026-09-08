def max_occurrences(lst):
    # Initialize a dictionary to store the frequency of each element
    frequency_dict = {}
    
    # Count the frequency of each element in the list
    for element in lst:
        if element in frequency_dict:
            frequency_dict[element] += 1
        else:
            frequency_dict[element] = 1
    
    # Find the element with the maximum frequency
    max_freq_element = max(frequency_dict, key=frequency_dict.get)
    
    return max_freq_element