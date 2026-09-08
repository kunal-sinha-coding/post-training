def Find_Max(lst):
    # Initialize the maximum length to 0
    max_length = 0
    # Initialize the maximum element to None
    max_element = None
    
    # Iterate through each sublist in the list
    for sublist in lst:
        # Check the length of the current sublist
        if len(sublist) > max_length:
            # Update the maximum length and the maximum element
            max_length = len(sublist)
            max_element = sublist[0]
    
    # Return the maximum element
    return max_element