def max_length(list_of_lists):
    # Initialize variables to store the maximum length and the corresponding list
    max_length = 0
    max_list = []
    
    # Iterate through each sublist in the list
    for sublist in list_of_lists:
        # Check if the current sublist is longer than the current maximum length
        if len(sublist) > max_length:
            # Update the maximum length and the corresponding list
            max_length = len(sublist)
            max_list = sublist
    
    # Return the maximum length and the corresponding list
    return max_length, max_list