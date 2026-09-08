def max_occurrences(lst):
    # Initialize a dictionary to store the frequency of each element
    frequency_dict = {}
    
    # Count the frequency of each element in the list
    for item in lst:
        if item in frequency_dict:
            frequency_dict[item] += 1
        else:
            frequency_dict[item] = 1
    
    # Find the maximum frequency
    max_freq = max(frequency_dict.values())
    
    # Find the element with the maximum frequency
    max_item = [item for item, freq in frequency_dict.items() if freq == max_freq][0]
    
    return max_item