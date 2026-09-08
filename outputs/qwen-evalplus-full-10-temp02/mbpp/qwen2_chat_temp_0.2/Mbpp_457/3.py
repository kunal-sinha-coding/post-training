def Find_Min(lst):
    # Initialize the minimum length to a large number
    min_len = float('inf')
    # Initialize the sublist with the first element of the list
    min_sublist = lst[0]
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Calculate the length of the current sublist
        sublist_len = len(sublist)
        # Update the minimum length if the current sublist is shorter
        if sublist_len < min_len:
            min_len = sublist_len
            min_sublist = sublist
    
    # Return the sublist with the minimum length
    return min_sublist