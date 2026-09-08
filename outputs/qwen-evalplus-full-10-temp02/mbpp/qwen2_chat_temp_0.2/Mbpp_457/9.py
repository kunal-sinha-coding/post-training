def Find_Min(lst):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    # Initialize the sublist with the first element of the list
    min_sublist = lst[0]
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Calculate the length of the current sublist
        current_length = len(sublist)
        
        # Check if the current sublist is shorter than the minimum length found so far
        if current_length < min_length:
            # Update the minimum length and the sublist
            min_length = current_length
            min_sublist = sublist
    
    # Return the sublist with the minimum length
    return min_sublist