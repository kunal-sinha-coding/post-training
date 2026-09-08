def Find_Max_Length(lists):
    # Initialize variables to keep track of the maximum length and the current length of the sublist
    max_length = 0
    current_length = 0
    
    # Iterate through each sublist in the list
    for sublist in lists:
        # Update the current length of the sublist
        current_length += len(sublist)
        
        # Update the maximum length if the current length is greater
        if current_length > max_length:
            max_length = current_length
    
    # Return the maximum length found
    return max_length