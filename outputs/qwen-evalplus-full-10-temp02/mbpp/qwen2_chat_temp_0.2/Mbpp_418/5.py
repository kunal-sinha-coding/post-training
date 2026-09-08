def Find_Max(lst):
    # Initialize the maximum length to 0
    max_length = 0
    # Initialize the variable to store the maximum element
    max_element = None
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Calculate the length of the current sublist
        length = len(sublist)
        # Check if the current sublist has a maximum length
        if length > max_length:
            # Update the maximum length and the maximum element
            max_length = length
            max_element = sublist
    
    # Return the maximum element
    return max_element