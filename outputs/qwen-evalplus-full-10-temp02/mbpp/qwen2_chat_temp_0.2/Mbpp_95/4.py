def Find_Min_Length(lists):
    # Initialize the minimum length to a large number
    min_length = float('inf')
    
    # Iterate through each sublist in the list
    for sublist in lists:
        # Calculate the length of the current sublist
        current_length = len(sublist)
        
        # Update the minimum length if the current sublist is smaller
        if current_length < min_length:
            min_length = current_length
    
    # Return the length of the smallest sublist
    return min_length