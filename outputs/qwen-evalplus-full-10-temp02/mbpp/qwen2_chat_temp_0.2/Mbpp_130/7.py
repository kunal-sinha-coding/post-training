def max_occurrences(lst):
    # Create a dictionary to count the frequency of each element in the list
    frequency = {}
    for item in lst:
        if item in frequency:
            frequency[item] += 1
        else:
            frequency[item] = 1
    
    # Find the maximum frequency
    max_freq = max(frequency.values())
    
    # Find the element with the maximum frequency
    max_item = [item for item, count in frequency.items() if count == max_freq][0]
    
    return max_item