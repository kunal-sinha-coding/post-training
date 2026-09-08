def max_occurrences(lst):
    # Create a dictionary to count occurrences of each element
    count_dict = {}
    for item in lst:
        if item in count_dict:
            count_dict[item] += 1
        else:
            count_dict[item] = 1
    
    # Find the maximum occurrence
    max_occurrence = max(count_dict.values())
    
    # Find the element with the maximum occurrence
    max_element = [item for item, count in count_dict.items() if count == max_occurrence][0]
    
    return max_element