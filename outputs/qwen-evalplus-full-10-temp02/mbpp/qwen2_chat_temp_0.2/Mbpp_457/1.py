def Find_Min(lst):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    # Initialize the sublist with the first element of the list
    min_sublist = lst[0]
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Calculate the length of the current sublist
        length = len(sublist)
        # Update the minimum length if the current sublist is smaller
        if length < min_length:
            min_length = length
            min_sublist = sublist
    
    # Return the sublist with the minimum length
    return min_sublist