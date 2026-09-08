def Find_Min(lst):
    # Initialize the minimum length to a large number
    min_len = float('inf')
    # Initialize the sublist with the first element of the list
    min_sublist = lst[0]
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Calculate the length of the current sublist
        sublist_len = len(sublist)
        # Check if the current sublist is shorter than the minimum length found so far
        if sublist_len < min_len:
            # Update the minimum length and the sublist
            min_len = sublist_len
            min_sublist = sublist
    
    # Return the sublist with the minimum length
    return min_sublist