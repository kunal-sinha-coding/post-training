def max_occurrences(arr):
    # Create a dictionary to count occurrences of each element
    count = {}
    for i in arr:
        if i in count:
            count[i] += 1
        else:
            count[i] = 1
    
    # Find the maximum occurrence
    max_occurrence = max(count.values())
    
    # Find the element with the maximum occurrence
    max_element = None
    for i, count in count.items():
        if count == max_occurrence:
            max_element = i
    
    return max_element