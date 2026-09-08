def max_occurrences(lst):
    # Initialize a dictionary to store the frequency of each element
    frequency = {}
    
    # Count the frequency of each element in the list
    for num in lst:
        if num in frequency:
            frequency[num] += 1
        else:
            frequency[num] = 1
    
    # Find the maximum frequency
    max_freq = max(frequency.values())
    
    # Find the element with the maximum frequency
    max_element = None
    for num, freq in frequency.items():
        if freq == max_freq:
            max_element = num
    
    return max_element