def max_occurrences(lst):
    # Create a dictionary to count occurrences of each element
    count_dict = {}
    for item in lst:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1
    
    # Find the maximum frequency
    max_freq = max(count_dict.values())
    
    # Find the element with the maximum frequency
    max_element = None
    for item, freq in count_dict.items():
        if freq == max_freq:
            max_element = item
    
    return max_element