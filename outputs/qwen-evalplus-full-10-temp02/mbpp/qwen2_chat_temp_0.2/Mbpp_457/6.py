def Find_Min(lists):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    # Initialize the sublist with the first element of the list
    min_sublist = lists[0]
    
    # Iterate through each sublist in the list
    for sublist in lists:
        # Calculate the length of the current sublist
        sublist_length = len(sublist)
        # Update the minimum length if the current sublist is shorter
        if sublist_length < min_length:
            min_length = sublist_length
            min_sublist = sublist
    
    # Return the sublist with the minimum length
    return min_sublist