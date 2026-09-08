def max_occurrences(lst):
    # Initialize a dictionary to store the frequency of each element
    frequency = {}
    
    # Count the frequency of each element in the list
    for num in lst:
        if num in frequency:
            frequency[num] += 1
        else:
            frequency[num] = 1
    
    # Find the element with the maximum frequency
    max_freq = max(frequency.values())
    max_item = None
    
    # Iterate through the frequency dictionary to find the item with the maximum frequency
    for item, freq in frequency.items():
        if freq == max_freq:
            max_item = item
    
    return max_item